# prompt/services/prompt_overpass_minimal.py

import requests
import logging
import time
from dataclasses import dataclass
from typing import List, Dict, Tuple, Optional
from datetime import datetime
import pytz
from timezonefinder import TimezoneFinder

logger = logging.getLogger(__name__)

OVERPASS_URL = "https://overpass-api.de/api/interpreter"

# NOTE:
# - OSM commonly uses amenity=marketplace (not shop=marketplace).
# - We keep your keys but fix the query to amenity=marketplace for reliability.
POI_TAGS = {
    "bus_stop":         'nwr["highway"="bus_stop"]',
    "subway_entrance":  'nwr["railway"="subway_entrance"]',
    "marketplace":      'nwr["amenity"="marketplace"]',
    "supermarket":      'nwr["shop"="supermarket"]',
    "convenience":      'nwr["shop"="convenience"]',
    "cafe":             'nwr["amenity"="cafe"]',
    "bakery":           'nwr["shop"="bakery"]',
    "ice_cream":        'nwr["amenity"="ice_cream"]',
    "park":             'nwr["leisure"="park"]',
    "river":            'nwr["waterway"="river"]',
    "office":           'nwr["amenity"="office"]',
    "school":           'nwr["amenity"="school"]',
    "university":       'nwr["amenity"="university"]',
}


@dataclass
class SceneInput:
    """Input data for generating a scene prompt."""
    lat: float
    lon: float
    city: str
    district: str
    temperature_c: float
    sky: str
    humidity_pct: int
    radius_m: int
    local_dt: datetime = None

    def __post_init__(self):
        # Set local datetime if not provided, using timezonefinder
        if self.local_dt is None:
            tf = TimezoneFinder()
            # Get timezone name from lat/lon
            tz_name = tf.timezone_at(lng=self.lon, lat=self.lat)

            # Default to UTC if timezone not found
            timezone = pytz.utc
            if tz_name:
                try:
                    timezone = pytz.timezone(tz_name)
                except pytz.UnknownTimeZoneError:
                    logger.warning(f"Could not find timezone '{tz_name}', defaulting to UTC.")

            self.local_dt = datetime.now(timezone)


def fetch_pois_overpass(lat: float, lon: float, radius_m: int, max_retries: int = 3) -> Dict[str, int]:
    """
    Fetch and count POIs via Overpass. Uses one request with multiple 'out count' statements.
    WARNING: Overpass 'out count' returns a list of count elements in the same order as queries.
             We map them back by preserving the POI_TAGS order.
    """
    # Build a single multi-statement query where each class is counted
    parts = [f'({tags}(around:{radius_m},{lat},{lon});); out count;' for tags in POI_TAGS.values()]
    query = "[out:json][timeout:25];" + "".join(parts)

    poi_counts: Dict[str, int] = {key: 0 for key in POI_TAGS.keys()}

    for attempt in range(max_retries):
        try:
            r = requests.post(OVERPASS_URL, data={"data": query}, timeout=30)
            r.raise_for_status()
            data = r.json()
            
            counts_in_order: List[int] = []
            # Each 'out count;' produces an element like:
            # {"type":"count","id":...,"tags":{"nodes":"x","ways":"y","relations":"z","total":"n"}}
            for el in data.get("elements", []):
                if el.get("type") == "count":
                    total = int(el.get("tags", {}).get("total", 0))
                    counts_in_order.append(total)

            # Map back to our keys by order
            for (key, _), total in zip(POI_TAGS.items(), counts_in_order):
                poi_counts[key] = total
            
            break  # Success, exit retry loop

        except requests.exceptions.RequestException as e:
            logger.warning(f"Overpass API request failed (attempt {attempt + 1}/{max_retries}): {e}")
            if attempt < max_retries - 1:
                time.sleep(2 ** attempt)  # Exponential backoff
                continue
            logger.error(f"Overpass API failed after {max_retries} attempts")
        except (ValueError, KeyError) as e:
            logger.error(f"Overpass parsing error: {e}")
            break  # Don't retry parsing errors
        except Exception as e:
            logger.error(f"Unexpected error with Overpass API: {e}")
            break

    # Keep only positive counts
    return {k: v for k, v in poi_counts.items() if v > 0}


def derive_intents(temperature_c: float, sky: str, humidity_pct: int, poi_counts: Dict[str, int]) -> List[str]:
    """Derive high-level intents from weather and POIs (no explicit dish names)."""
    intents: List[str] = []

    # Weather-based
    if temperature_c >= 27:
        intents += ["heat_relief", "hydration", "lighter_meal"]
    if temperature_c <= 5:
        intents += ["warmth", "hearty_meal"]
    if any(k in sky.lower() for k in ["sunny", "clear"]):
        intents += ["very_sunny"]
    if humidity_pct >= 70:
        intents += ["high_humidity"]

    # POI-based
    if any(k in poi_counts for k in ["bus_stop", "subway_entrance"]):
        intents += ["portable", "quick_serve", "low_wait"]
    if "marketplace" in poi_counts or "supermarket" in poi_counts:
        intents += ["street_food_friendly"]
    if any(k in poi_counts for k in ["cafe", "bakery", "ice_cream"]):
        intents += ["dessert_pairing_possible", "iced_beverage_pair"]
    if any(k in poi_counts for k in ["park", "river"]):
        intents += ["picnic_ready", "shareable"]
    if any(k in poi_counts for k in ["office", "school", "university"]):
        intents += ["rush_lunch", "budget_sensitive"]

    # De-dup while preserving order
    seen = set()
    deduped = []
    for it in intents:
        if it not in seen:
            deduped.append(it)
            seen.add(it)
    return deduped


# ---------- NEW: Bias derivation (text + tags) ----------
def derive_bias_explanation(
        scene: SceneInput, poi_counts: Dict[str, int], intents: List[str]
) -> Tuple[List[str], List[str]]:
    """
    Build human-readable bias bullets and unified bias tags for the [BIAS] section.
    Returns (bias_lines, bias_tags)
    """
    bias_lines: List[str] = []
    bias_tags: List[str] = []

    # Weather bias
    if scene.temperature_c >= 27:
        bias_lines.append("Weather: hot (>=27°C) → prefer cold/light items, hydration, gentle acidity.")
        bias_tags += ["cold_pref", "light_pref", "hydration_pref"]
    elif scene.temperature_c <= 5:
        bias_lines.append("Weather: cold (<=5°C) → prefer hot/hearty items.")
        bias_tags += ["hot_pref", "hearty_pref"]

    if "very_sunny" in intents:
        bias_lines.append("Sun: very sunny → refreshing/iced options acceptable.")
        bias_tags += ["iced_ok", "refreshing_pref"]

    if "high_humidity" in intents:
        bias_lines.append("Humidity: high → crisp/acidic or broth-based relief acceptable.")
        bias_tags += ["acid_ok", "broth_ok"]

    # POI bias (only if present)
    if any(k in poi_counts for k in ["bus_stop", "subway_entrance"]):
        bias_lines.append("Transit nearby → quick-serve, portable formats prioritized.")
        bias_tags += ["quick_serve_pref", "portable_pref", "low_wait_pref"]

    if any(k in poi_counts for k in ["marketplace", "supermarket"]):
        bias_lines.append("Market area → casual, street-food-friendly formats acceptable.")
        bias_tags += ["street_food_pref"]

    if any(k in poi_counts for k in ["cafe", "bakery", "ice_cream"]):
        bias_lines.append("Cafe/dessert spots nearby → dessert/iced drink pairing acceptable.")
        bias_tags += ["dessert_pairing_ok", "iced_beverage_pair_ok"]

    if any(k in poi_counts for k in ["park", "river"]):
        bias_lines.append("Outdoor spots → picnic-ready, shareable formats prioritized.")
        bias_tags += ["picnic_pref", "shareable_pref"]

    if any(k in poi_counts for k in ["office", "school", "university"]):
        bias_lines.append("Office/school area → rush-lunch, budget-sensitive options prioritized.")
        bias_tags += ["rush_lunch_pref", "budget_pref"]

    # De-dup bias tags
    seen = set()
    bias_tags_final = []
    for t in bias_tags:
        if t not in seen:
            bias_tags_final.append(t)
            seen.add(t)

    # Fallback if no biases detected
    if not bias_lines:
        bias_lines.append("No strong POI bias; default to weather/time suitability.")
    if not bias_tags_final:
        bias_tags_final = ["context_only"]

    return bias_lines, bias_tags_final


def build_paragraphica_prompt(scene: SceneInput, poi_counts: Dict[str, int], intents: List[str]) -> str:
    """Construct the final Paragraphica-style prompt string (with [BIAS] section)."""
    # Scene formatting
    location = f"{scene.district}, {scene.city} (lat: {scene.lat}, lon: {scene.lon})"
    local_time_str = scene.local_dt.strftime("%Y-%m-%d %A, %H:%M")
    weather = f"{scene.temperature_c}°C, {scene.sky}, humidity {scene.humidity_pct}%"

    # Surroundings
    surroundings_str = "nothing specific"
    if poi_counts:
        surroundings_str = ", ".join(k.replace("_", " ") for k in poi_counts.keys()) + " nearby"

    # Intents/Bias
    intents_str = ", ".join(intents) if intents else "no specific intents"
    bias_lines, bias_tags = derive_bias_explanation(scene, poi_counts, intents)
    bias_lines_str = "\n- ".join(bias_lines)
    bias_tags_str = ", ".join(bias_tags)

    prompt = f'''[SCENE]
    - Location: {location}
    - Datetime (local): {local_time_str}
    - Weather: {weather}
    - Surroundings: {surroundings_str}
    
    [INTENT]
    - Context intents: {intents_str}
    
    [BIAS]
    - {bias_lines_str}
    - Bias tags: {bias_tags_str}
    - Guidance: adhere to bias tags; stay realistic for the given region; avoid exotic items.
    
    [RULES]
    - Your primary goal is to suggest a single, specific food or drink menu item.
    - The menu must be common and culturally appropriate for the given region/country.
    - DO NOT mention any specific restaurant, brand, or store name.
    - DO NOT use any of the words from the 'Surroundings' list in your suggestion.
    - The suggestion must be realistic and highly relevant to the scene, especially the weather and derived intents.
    - The output format MUST be a single, clean JSON object.
    
    [SCORING]
    - High score for items that are familiar, locally popular, and seasonally appropriate.
    - High score for items that align well with multiple intents (e.g., light and hydrating in hot weather).
    - Low score for overly exotic, unrealistic, or culturally irrelevant items.
    - Low score for generic, low-effort suggestions (e.g., "water", "snack").
    - Low score for suggestions that ignore key intents (e.g., a hot, heavy soup on a sweltering day).
    
    [OUTPUT]
    - Your response must be only a single JSON object and nothing else.
    - The JSON object must have two keys: "suggestion" (string) and "reason" (string).
    '''

    return prompt


def generate_prompt(scene_input: SceneInput) -> str:
    """Orchestrate the prompt generation process."""
    poi_counts = fetch_pois_overpass(scene_input.lat, scene_input.lon, scene_input.radius_m)
    intents = derive_intents(scene_input.temperature_c, scene_input.sky, scene_input.humidity_pct, poi_counts)
    final_prompt = build_paragraphica_prompt(scene_input, poi_counts, intents)
    return final_prompt
