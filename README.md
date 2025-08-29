# ParaGourmet: Paragraphica-style Food Prompt Generator

This is a Django-based API server that generates contextual food and drink prompts in the style of Paragraphica. It uses location, weather, and nearby points of interest (from OpenStreetMap via Overpass API) to create detailed prompts for an AI to generate menu suggestions.

The key feature is that it **does not** suggest menu items directly. Instead, it creates a rich context with constraints, intents, and scoring rules, guiding an AI to make creative and relevant suggestions.

## Features

- **Health Check:** `GET /health` endpoint for monitoring.
- **Prompt Generation:** `GET /api/prompt` endpoint to generate prompts.
- **Contextual Analysis:**
  - **Location:** City and district level (country is omitted).
  - **Weather:** Temperature, sky conditions, and humidity.
  - **Time:** Current local date and time.
  - **Surroundings:** Uses the Overpass API to find nearby POIs like cafes, parks, bus stops, etc.
- **Intent Derivation:** Infers user intents like `heat_relief`, `picnic_ready`, or `rush_lunch` based on the context.
- **Dynamic Prompting:** Builds a detailed prompt with `[SCENE]`, `[INTENT]`, `[RULES]`, and `[SCORING]` sections.

## Tech Stack

- **Backend:** Django
- **Dependencies:** `requests` (for Overpass API), `python-dotenv` (for environment management)
- **Database:** SQLite (default)

---

## Setup and Installation

### 1. Create a Virtual Environment

**On Windows:**
```bash
python -m venv venv
.\venv\Scripts\activate
```

**On macOS/Linux:**
```bash
python3 -m venv venv
source venv/bin/activate
```

### 2. Install Dependencies

Install the required packages from `requirements.txt`. The Django version depends on your Python version.

**For Python 3.10 or newer (recommended):**
First, edit `requirements.txt` and change the Django version:
```
# Django>=5.0,<6.0
Django>=5.0,<6.0
```
Then install:
```bash
pip install -r requirements.txt
```

**For Python 3.8/3.9 (LTS path):**
Use the `requirements.txt` as is.
```bash
pip install -r requirements.txt
```

### 3. Configure Environment Variables

Create a `.env` file in the project root by copying the example file.

```bash
copy .env.example .env  # Windows
# or
cp .env.example .env    # macOS/Linux
```

Open the `.env` file and set your `DJANGO_SECRET_KEY`. You can generate one using an online tool or a Python script.

```
DJANGO_SECRET_KEY="your-super-secret-key-goes-here"
DEBUG=True
ALLOWED_HOSTS=localhost,127.0.0.1
```

---

## Running the Server

### 1. Apply Database Migrations

Run the initial database migrations.

```bash
python manage.py migrate
```

### 2. Start the Development Server

The server will run on `http://0.0.0.0:8000/`.

```bash
python manage.py runserver 0.0.0.0:8000
```

---

## API Usage and Testing

### Health Check

You can check if the server is running correctly.

```bash
curl http://127.0.0.1:8000/health
```

Expected Response:
```json
{ "ok": true }
```

### Prompt Generation

Send a GET request to the `/api/prompt` endpoint with the required query parameters.

**Example Request (using curl):**

This example uses coordinates for Seongsu-dong, Seoul on a hot day.

```bash
curl -G "http://127.0.0.1:8000/api/prompt" \
  --data-urlencode "lat=37.544" \
  --data-urlencode "lon=127.056" \
  --data-urlencode "city=Seoul" \
  --data-urlencode "district=Seongsu-dong" \
  --data-urlencode "temp_c=28" \
  --data-urlencode "sky=very sunny" \
  --data-urlencode "humidity=60" \
  --data-urlencode "radius=350"
```

**Example Response:**

The response will contain a detailed prompt for an AI. The `Surroundings` and `Intents` will vary based on the live data from the Overpass API.

```json
{
    "prompt": "[SCENE]\n- Location: Seongsu-dong, Seoul (lat: 37.544, lon: 127.056)\n- Datetime (local): 2025-08-29 Friday, 14:30\n- Weather: 28°C, very sunny, humidity 60%\n- Surroundings: bus stop, cafe, convenience, office, subway entrance nearby\n\n[INTENT]\n- Context intents: budget_sensitive, dessert_pairing_possible, heat_relief, hydration, iced_beverage_pair, lighter_meal, portable, quick_serve, low_wait, rush_lunch, very_sunny\n\n[RULES]\n- Your primary goal is to suggest a single, specific food or drink menu item.\n- DO NOT mention any specific restaurant, brand, or store name.\n- DO NOT use any of the words from the \'Surroundings\' list in your suggestion.\n- The suggestion must be highly relevant to the scene, especially the weather and derived intents.\n- The output format MUST be a single, clean JSON object.\n\n[SCORING]\n- High score for creative, non-obvious items that perfectly fit the context (e.g., \"chilled cucumber soup\" on a hot day instead of just \"iced coffee\").\n- High score for items that align with multiple intents (e.g., a shareable, portable item for a picnic-ready context).\n- Low score for generic, low-effort suggestions (e.g., \"water\", \"snack\").\n- Low score for suggestions that ignore key intents (e.g., a hot, heavy soup on a sweltering day).\n\n[OUTPUT]\n- Your response must be only a single JSON object and nothing else.\n- The JSON object must have two keys: \"suggestion\" (string) and \"reason\" (string).\n- Example: {\"suggestion\": \"Iced Yuja-ade\", \"reason\": \"A refreshing and hydrating citrus drink that provides heat relief on a very sunny day, perfect for a quick grab-and-go option.\"}\n"
}
```
