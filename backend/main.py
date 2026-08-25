from fastapi import FastAPI 
from services.geocoder import get_coordinates
from services.weather import get_weather_forecast, analyze_forecast
from services.satellite import get_satellite_indices, analyze_satellite
from services.stress_engine import calculate_stress, generate_message
from services.stress_engine import calculate_stress, generate_message, level_to_score_and_bucket

app=FastAPI()

from pydantic import BaseModel

class AnalyzeRequest(BaseModel):
    village: str
    crop: str

LEVEL_MAP = {"green": "low", "yellow": "moderate", "red": "high"}

@app.get('/')
def read_root():
  return {'message':'Jalsense backend is running'}

@app.get('/predict')
def predict(village: str, crop: str):

  location=get_coordinates(village)

  if location is None:
    return {'error':f"could not ind location of village:{village}"}

  raw_weather=get_weather_forecast(location['latitude'],location['longitude'])
  weather=analyze_forecast(raw_weather)

  raw_satellite=get_satellite_indices(location['latitude'],location['longitude'])
  satellite=analyze_satellite(raw_satellite)

  if satellite is None:
    return {"error": "Satellite data unavailable for this location right now. Please try again later."}

  stress_level=calculate_stress(satellite, weather, crop)
  message=generate_message(stress_level, village, weather)
  return {
        "village": village,
        "crop": crop,
        "latitude": location["latitude"],
        "longitude": location["longitude"],
        "resolved_location": location["resolved_name"],
        "location_source": location["source"],
        "weather": weather,
        "satellite": satellite,
        "stress_level": stress_level,
        "alert_text_hindi": message["hindi"],
        "alert_text_english": message["english"]
    }

@app.post("/api/analyze")
def analyze(request: AnalyzeRequest):
    village = request.village
    crop = request.crop

    location = get_coordinates(village)
    if location is None:
        return {"error": f"Could not find location for village: {village}"}

    raw_weather = get_weather_forecast(location["latitude"], location["longitude"])
    weather = analyze_forecast(raw_weather)

    raw_satellite = get_satellite_indices(location["latitude"], location["longitude"])
    satellite = analyze_satellite(raw_satellite)

    if satellite is None:
        return {"error": "Satellite data unavailable for this location right now."}

    level = calculate_stress(satellite, weather, crop)
    score, bucket = level_to_score_and_bucket(level, satellite, weather)
    message = generate_message(bucket, village, weather)

    return {
        "village": village,
        "crop": crop,
        "stress_score": score,
        "stress_level": bucket,
        "ndvi": satellite["ndvi"],
        "ndwi": satellite["ndwi"],
        "rain_probability": weather["rain_probability_tomorrow"],
        "recommendation_hi": message["hindi"]
    }