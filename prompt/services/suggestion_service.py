# prompt/services/suggestion_service.py

import os
import json
import logging
from openai import OpenAI
from googleapiclient.discovery import build

logger = logging.getLogger(__name__)

# --- OpenAI Service --- #

def get_ai_suggestion(prompt_text: str, lang: str = 'en', diversity_mode: bool = False) -> dict | None:
    """
    Sends a prompt to OpenAI GPT model and gets a food suggestion.
    Returns a dictionary with 'suggestion' and 'reason'.
    """
    api_key = os.getenv("OPENAI_API_KEY")
    if not api_key:
        logger.error("OPENAI_API_KEY not found in environment variables.")
        return None

    client = OpenAI(api_key=api_key)

    system_message_content = "You are an AI that suggests a single food or drink item based on a detailed prompt. You must follow all rules and output only a single, clean JSON object with two keys: suggestion and reason."
    if lang == 'ko':
        system_message_content += " 한국어로 응답해줘. 대신에 친근하고 인스타 피드에서 볼법한 어투로 작성해줘"
    elif lang == 'en':
        system_message_content += " Respond in English."

    if diversity_mode:
        system_message_content += " 이전에 같은 요청이 있었다면, 다른 적합한 옵션을 제안해 주세요."

    try:
        response = client.chat.completions.create(
            model="gpt-4.1-mini",  # JSON 강제 지원
            messages=[
                {"role": "system", "content": system_message_content},
                {"role": "user", "content": prompt_text}
            ],
            temperature=0.8,
            max_completion_tokens=200,
            response_format={"type": "json_object"}  # JSON 강제 가능
        )
        
        content = response.choices[0].message.content
        suggestion_data = json.loads(content)

        if "suggestion" in suggestion_data and "reason" in suggestion_data:
            return suggestion_data
        else:
            logger.error(f"AI response JSON is missing required keys: {content}")
            return None

    except Exception as e:
        logger.error(f"An error occurred with the OpenAI API call: {e}")
        return None

# --- Google Image Search Service --- #

def get_image_url(query: str, lang: str = 'en') -> str | None:
    """
    Searches for an image using Google Custom Search API and returns the URL of the first result.
    """
    api_key = os.getenv("CUSTOM_SEARCH_API_KEY")
    search_engine_id = os.getenv("SEARCH_ENGINE_ID")

    if not api_key or not search_engine_id:
        logger.error("CUSTOM_SEARCH_API_KEY or SEARCH_ENGINE_ID not found.")
        return None

    try:
        service = build("customsearch", "v1", developerKey=api_key)
        
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
            num=1, # We only need the first result
            imgSize="LARGE",
            safe="high"
        ).execute()

        items = result.get("items", [])
        if items:
            return items[0].get("link")
        else:
            logger.warning(f"No image results found for query: {query}")
            return None

    except Exception as e:
        logger.error(f"An error occurred with the Google Image Search API call: {e}")
        return ("Nonege Search API call: {e}")
        return None