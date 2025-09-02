# prompt/tests.py

import json
from unittest.mock import patch, MagicMock
from django.test import TestCase
from django.urls import reverse
from .services.suggestion_service import get_ai_suggestion, get_image_url
from .services.prompt_overpass_minimal import fetch_pois_overpass, derive_intents, SceneInput

class PromptAppTests(TestCase):

    def test_health_check_view(self):
        """
        Tests that the health check endpoint returns a 200 OK response.
        """
        url = reverse('health_check')
        response = self.client.get(url)
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.json(), {"ok": True})

    def test_prompt_view_missing_params(self):
        """
        Tests that the prompt view returns a 400 Bad Request with missing params.
        """
        url = reverse('prompt_api')
        response = self.client.get(url) # No params
        self.assertEqual(response.status_code, 400)

    def test_prompt_view_invalid_params(self):
        """
        Tests that the prompt view returns a 400 Bad Request with invalid params.
        """
        url = reverse('prompt_api')
        # 'lat' is not a float
        query_params = "?lat=invalid&lon=127.056&city=Seoul&district=Seongsu-dong&temp_c=28&sky=very%20sunny&humidity=60"
        response = self.client.get(url + query_params)
        self.assertEqual(response.status_code, 400)

    def test_prompt_view_success(self):
        """
        Tests a successful call to the prompt view.
        This is a basic check and does not validate the Overpass call.
        We mock the service layer to avoid external dependencies in unit tests.
        """
        # In a real-world scenario, you would mock 'generate_prompt'
        # from .services.prompt_overpass_minimal
        url = reverse('prompt_api')
        query_params = "?lat=37.544&lon=127.056&city=Seoul&district=Seongsu-dong&temp_c=28&sky=very%20sunny&humidity=60"
        response = self.client.get(url + query_params)
        self.assertEqual(response.status_code, 200)
        data = response.json()
        self.assertIn("prompt", data)
        self.assertIn("[SCENE]", data["prompt"])
        self.assertIn("Seongsu-dong, Seoul", data["prompt"])


class SuggestionServiceTests(TestCase):
    """Tests for the suggestion service functions."""

    @patch('prompt.services.suggestion_service._get_openai_client')
    def test_get_ai_suggestion_success(self, mock_get_client):
        """Test successful OpenAI API call."""
        # Mock client and response
        mock_client = MagicMock()
        mock_get_client.return_value = mock_client
        
        mock_response = MagicMock()
        mock_response.choices = [MagicMock()]
        mock_response.choices[0].message.content = '{"suggestion": "Test Food", "reason": "Test reason"}'
        mock_client.chat.completions.create.return_value = mock_response
        
        result = get_ai_suggestion("test prompt", "en")
        
        self.assertIsNotNone(result)
        self.assertEqual(result["suggestion"], "Test Food")
        self.assertEqual(result["reason"], "Test reason")

    @patch('prompt.services.suggestion_service._get_openai_client')
    def test_get_ai_suggestion_no_client(self, mock_get_client):
        """Test when OpenAI client is not available."""
        mock_get_client.return_value = None
        
        result = get_ai_suggestion("test prompt")
        
        self.assertIsNone(result)

    @patch('prompt.services.suggestion_service._get_google_service')
    @patch('os.getenv')
    def test_get_image_url_success(self, mock_getenv, mock_get_service):
        """Test successful Google Image Search."""
        mock_getenv.return_value = "test-engine-id"
        
        mock_service = MagicMock()
        mock_get_service.return_value = mock_service
        
        mock_result = {"items": [{"link": "https://example.com/image.jpg"}]}
        mock_service.cse().list().execute.return_value = mock_result
        
        result = get_image_url("test query")
        
        self.assertEqual(result, "https://example.com/image.jpg")

    @patch('prompt.services.suggestion_service._get_google_service')
    def test_get_image_url_no_service(self, mock_get_service):
        """Test when Google service is not available."""
        mock_get_service.return_value = None
        
        result = get_image_url("test query")
        
        self.assertIsNone(result)


class PromptServiceTests(TestCase):
    """Tests for the prompt generation service functions."""

    def test_derive_intents_hot_weather(self):
        """Test intent derivation for hot weather."""
        intents = derive_intents(30.0, "sunny", 70, {"cafe": 5})
        
        self.assertIn("heat_relief", intents)
        self.assertIn("hydration", intents)
        self.assertIn("lighter_meal", intents)

    def test_derive_intents_cold_weather(self):
        """Test intent derivation for cold weather."""
        intents = derive_intents(5.0, "cloudy", 40, {"bakery": 3})
        
        self.assertIn("warmth", intents)
        self.assertIn("hearty_meal", intents)

    @patch('requests.post')
    def test_fetch_pois_overpass_success(self, mock_post):
        """Test successful Overpass API call."""
        mock_response = MagicMock()
        mock_response.json.return_value = {
            "elements": [
                {"type": "count", "tags": {"total": "5"}},
                {"type": "count", "tags": {"total": "3"}},
            ]
        }
        mock_response.raise_for_status.return_value = None
        mock_post.return_value = mock_response
        
        result = fetch_pois_overpass(37.544, 127.056, 350)
        
        self.assertIsInstance(result, dict)
        # Should only return positive counts
        for count in result.values():
            self.assertGreater(count, 0)

    @patch('requests.post')
    def test_fetch_pois_overpass_failure(self, mock_post):
        """Test Overpass API failure handling."""
        mock_post.side_effect = Exception("Network error")
        
        result = fetch_pois_overpass(37.544, 127.056, 350)
        
        self.assertEqual(result, {})  # Should return empty dict on failure

    def test_scene_input_timezone(self):
        """Test SceneInput timezone handling."""
        scene = SceneInput(
            lat=37.544, lon=127.056, city="Seoul", district="Gangnam",
            temperature_c=25.0, sky="sunny", humidity_pct=60, radius_m=500
        )
        
        self.assertIsNotNone(scene.local_dt)
        # Should default to some timezone (UTC if location not found)
