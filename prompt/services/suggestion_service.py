# prompt/services/suggestion_service.py

import os
import json
import logging
import time
from typing import Optional, Dict, Any
from openai import OpenAI, OpenAIError
from googleapiclient.discovery import build
from googleapiclient.errors import HttpError

logger = logging.getLogger(__name__)

# --- API Client Instances --- #
_openai_client: Optional[OpenAI] = None
_google_service: Optional[Any] = None

def _get_openai_client() -> Optional[OpenAI]:
    """Get or create OpenAI client instance."""
    global _openai_client
    if _openai_client is None:
        api_key = os.getenv("OPENAI_API_KEY")
        if not api_key:
            logger.error("OPENAI_API_KEY not found in environment variables.")
            return None
        _openai_client = OpenAI(api_key=api_key)
    return _openai_client

def _get_google_service() -> Optional[Any]:
    """Get or create Google Custom Search service instance."""
    global _google_service
    if _google_service is None:
        api_key = os.getenv("CUSTOM_SEARCH_API_KEY")
        if not api_key:
            logger.error("CUSTOM_SEARCH_API_KEY not found in environment variables.")
            return None
        try:
            _google_service = build("customsearch", "v1", developerKey=api_key)
        except Exception as e:
            logger.error(f"Failed to build Google service: {e}")
            return None
    return _google_service

# --- OpenAI Service --- #

def get_ai_suggestion(prompt_text: str, lang: str = 'en', diversity_mode: bool = False, max_retries: int = 3) -> Optional[Dict[str, Any]]:
    """
    Sends a prompt to OpenAI GPT model and gets a food suggestion.
    Returns a dictionary with 'suggestion' and 'reason'.
    """
    client = _get_openai_client()
    if not client:
        return None

    system_message_content = "You are an AI that suggests a single food or drink item based on a detailed prompt. You must follow all rules and output only a single, clean JSON object with two keys: suggestion and reason."
    if lang == 'ko':
        system_message_content += " 한국어로 응답해줘. 대신에 친근하고 인스타 피드에서 볼법한 어투로 작성해줘"
    elif lang == 'en':
        system_message_content += " Respond in English."

    if diversity_mode:
        system_message_content += " 이전에 같은 요청이 있었다면, 다른 적합한 옵션을 제안해 주세요."

    for attempt in range(max_retries):
        try:
            response = client.chat.completions.create(
                model="gpt-4o-mini",
                messages=[
                    {"role": "system", "content": system_message_content},
                    {"role": "user", "content": prompt_text}
                ],
                temperature=0.8,
                max_completion_tokens=200,
                response_format={"type": "json_object"},
                timeout=30.0  # 30 second timeout
            )
            
            content = response.choices[0].message.content
            suggestion_data = json.loads(content)

            if "suggestion" in suggestion_data and "reason" in suggestion_data:
                return suggestion_data
            else:
                logger.error(f"AI response JSON is missing required keys: {content}")
                return None

        except OpenAIError as e:
            logger.warning(
                "OpenAI API error",
                extra={
                    "attempt": attempt + 1,
                    "max_retries": max_retries,
                    "error": str(e),
                    "function": "get_ai_suggestion"
                }
            )
            if attempt < max_retries - 1:
                time.sleep(2 ** attempt)  # Exponential backoff
                continue
            logger.error(
                "OpenAI API failed after all retries",
                extra={
                    "max_retries": max_retries,
                    "error": str(e),
                    "function": "get_ai_suggestion"
                }
            )
            return None
        except json.JSONDecodeError as e:
            logger.error(f"Failed to parse AI response as JSON: {e}")
            return None
        except Exception as e:
            logger.error(f"Unexpected error with OpenAI API call: {e}")
            return None

# --- Google Image Search Service --- #

def get_image_url(query: str, lang: str = 'en', max_retries: int = 3) -> Optional[str]:
    """
    Searches for an image using Google Custom Search API and returns the URL of the first result.
    """
    service = _get_google_service()
    search_engine_id = os.getenv("SEARCH_ENGINE_ID")
    
    if not service or not search_engine_id:
        logger.error("Google service or SEARCH_ENGINE_ID not available.")
        return None

    for attempt in range(max_retries):
        try:
            
            # Adjust search query based on language
            search_query = f"{query} food photography"
            if lang == 'ko':
                search_query = f"{query} 음식 사진"
            elif lang == 'en':
                search_query = f"{query} food photography"

            result = service.cse().list(
                q=search_query,
                cx=search_engine_id,
                searchType="image",
                num=1,
                imgSize="LARGE",
                safe="high"
            ).execute()

            items = result.get("items", [])
            if items:
                return items[0].get("link")
            else:
                logger.warning(f"No image results found for query: {query}")
                return None

        except HttpError as e:
            logger.warning(f"Google API HTTP error (attempt {attempt + 1}/{max_retries}): {e}")
            if attempt < max_retries - 1:
                time.sleep(2 ** attempt)  # Exponential backoff
                continue
            logger.error(f"Google Image Search failed after {max_retries} attempts")
            return None
        except Exception as e:
            logger.error(f"Unexpected error with Google Image Search API call: {e}")
            return None