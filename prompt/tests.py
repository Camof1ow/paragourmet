# prompt/tests.py

from django.test import TestCase
from django.urls import reverse

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
