# 🌾 JalSense — AI Water Stress Early Warning for Marginal Farmers

A zero-app, voice-first WhatsApp bot that detects water stress in a farmer's field using real satellite imagery — and delivers the alert as a voice message in Hindi.

## The Problem

India has 140+ million smallholder farmers who lose 20–30% of their crop yield every year due to poor irrigation timing. Existing satellite-based solutions (like Farmonaut) are built for agribusinesses — they require smartphone apps, account registration, and English literacy. The individual marginal farmer is left unserved.

## What JalSense Does

A farmer sends a WhatsApp message with just their village name and crop — in Hindi. JalSense automatically:

1. Geocodes the village to real coordinates (local database + OpenStreetMap fallback)
2. Pulls live Sentinel-2 satellite imagery (Copernicus Data Space Ecosystem)
3. Calculates NDWI (water stress) and NDVI (vegetation health) for that exact location
4. Fetches a real 10-day weather forecast (Open-Meteo)
5. Runs a crop-specific stress prediction model
6. Replies with a Hindi voice note explaining the situation and what to do

No app download. No login. No subscription. Just WhatsApp.

## Tech Stack

- **Backend**: Python, FastAPI, SQLAlchemy, SQLite
- **Satellite Data**: Sentinel-2 via Copernicus Data Space Ecosystem (Statistical API)
- **Weather**: Open-Meteo API
- **Geocoding**: Local CSV + OpenStreetMap Nominatim
- **WhatsApp Bot**: Twilio WhatsApp API
- **Voice Generation**: Microsoft Edge TTS (Hindi neural voice)
- **Frontend Dashboard**: React, Tailwind CSS, Leaflet, Axios

## Project Structure

quantumhacks/
├── backend/ # FastAPI backend — geocoding, weather, satellite, stress engine, database
├── whatsapp/ # Twilio WhatsApp bot, conversation handler, TTS
└── frontend/ # React dashboard — live demo, farmer map, stats


## Running Locally

**Backend:**
```bash
cd backend
python -m venv venv
venv\Scripts\activate
pip install -r requirements.txt
uvicorn main:app --reload
```

**Frontend:**
```bash
cd frontend
npm install
npm run dev
```

**WhatsApp Bot:**
```bash
cd whatsapp
python -m venv venv
venv\Scripts\activate
pip install -r requirements.txt
python main.py
```

## Attribution

- Satellite imagery: Copernicus Sentinel-2 data via Copernicus Data Space Ecosystem
- Weather data: Open-Meteo
- Geocoding: OpenStreetMap Nominatim
- Voice synthesis: Microsoft Edge TTS

## Team

Built by [Rakshita] and [Bhanu] for Hack the Habitat 2026.
