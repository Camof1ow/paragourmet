# prompt/views.py

import logging
from django.http import JsonResponse, HttpRequest, HttpResponseBadRequest
from django.shortcuts import render
from .services.prompt_overpass_minimal import generate_prompt, SceneInput
from .services.suggestion_service import get_ai_suggestion, get_image_url
import os # Added for os.getenv in index_view

logger = logging.getLogger(__name__)

def health_check_view(request: HttpRequest) -> JsonResponse:
    """
    A simple health check endpoint.
    """
    return JsonResponse({"ok": True})

def prompt_view(request: HttpRequest) -> JsonResponse:
    """
    Generates a Paragraphica-style prompt based on query parameters.
    """
    if request.method != 'GET':
        return JsonResponse({'error': 'Only GET method is allowed'}, status=405)

    try:
        # Extract and validate required parameters
        scene_input = SceneInput(
            lat=float(request.GET['lat']),
            lon=float(request.GET['lon']),
            city=request.GET['city'],
            district=request.GET['district'],
            temperature_c=float(request.GET['temp_c']),
            sky=request.GET['sky'],
            humidity_pct=parse_humidity(request.GET.get('humidity', '0')), # Modified
            radius_m=int(request.GET.get('radius', 350))
        )

        # Generate the prompt using the service
        final_prompt = generate_prompt(scene_input)

        return JsonResponse({"prompt": final_prompt})

    except (KeyError, ValueError) as e:
        logger.warning(f"Bad request to prompt_view: {e}")
        return HttpResponseBadRequest(f"Invalid or missing query parameters: {e}")
    except Exception as e:
        logger.error(f"Internal server error in prompt_view: {e}", exc_info=True)
        return JsonResponse({'error': 'An internal server error occurred.'}, status=500)

def suggestion_view(request: HttpRequest) -> JsonResponse:
    """
    Full-cycle endpoint that generates a prompt, gets an AI suggestion,
    and finds an image for it.
    """
    if request.method != 'GET':
        return JsonResponse({'error': 'Only GET method is allowed'}, status=405)

    lang = request.GET.get('lang', 'en') # Get language from query param, default to 'en'
    diversity_mode = request.GET.get('diversity_mode', 'false').lower() == 'true' # Get diversity_mode from query param

    try:
        # 1. Get scene input from query parameters
        scene_input = SceneInput(
            lat=float(request.GET['lat']),
            lon=float(request.GET['lon']),
            city=request.GET['city'],
            district=request.GET['district'],
            temperature_c=float(request.GET['temp_c']),
            sky=request.GET['sky'],
            humidity_pct=parse_humidity(request.GET.get('humidity', '0')), # Modified
            radius_m=int(request.GET.get('radius', 350))
        )
    except (KeyError, ValueError) as e:
        return HttpResponseBadRequest(f"Invalid or missing query parameters: {e}")

    # 2. Generate the prompt
    prompt_text = generate_prompt(scene_input)
    if not prompt_text:
        return JsonResponse({'error': 'Failed to generate prompt.'}, status=500)

    # 3. Get AI suggestion
    suggestion_data = get_ai_suggestion(prompt_text, lang) # Pass lang
    if not suggestion_data:
        return JsonResponse({'error': 'Failed to get suggestion from AI.'}, status=500)

    # 4. Get image URL for the suggestion
    food_name = suggestion_data.get("suggestion")
    image_url = get_image_url(food_name, lang) # Pass lang

    # 5. Combine and return the final result
    final_response = {
        "suggestion": food_name,
        "reason": suggestion_data.get("reason"),
        "image_url": image_url or "No image found"
    }

    return JsonResponse(final_response)

def index_view(request: HttpRequest, lang: str = 'ko'): # lang parameter from URL
    context = {'lang': lang}
    return render(request, 'index.html', context)

def parse_humidity(humidity_str: str) -> int:
    """
    Parses humidity string to integer, handling 'N/A' or invalid values.
    """
    try:
        return int(humidity_str)
    except (ValueError, TypeError):
        return 0 # Default to 0 if not a valid integer or 'N/A'
