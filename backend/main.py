from fastapi import FastAPI 
from services.geocoder import get_coordinates
from services.weather import get_weather_forecast, analyze_forecast
from services.satellite import get_satellite_indices, analyze_satellite
from services.stress_engine import calculate_stress, generate_message
from services.stress_engine import calculate_stress, generate_message, level_to_score_and_bucket
from database import SessionLocal
from models import Farmer, Alert
from sqlalchemy.orm import Session
from fastapi import FastAPI, Depends
from datetime import date
from fastapi.middleware.cors import CORSMiddleware

app=FastAPI()

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

from pydantic import BaseModel

class AnalyzeRequest(BaseModel):
    village: str
    crop: str
    phone_number: str= 'unknown'

LEVEL_MAP = {"green": "low", "yellow": "moderate", "red": "high"}

def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()

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
def analyze(request: AnalyzeRequest, db: Session = Depends(get_db)):
    village = request.village
    crop = request.crop
    phone_number = request.phone_number

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

    farmer = db.query(Farmer).filter(Farmer.phone_number == phone_number).first()

    if farmer is None:
        farmer = Farmer(
            phone_number=phone_number,
            village_name=village,
            crop_name=crop,
            latitude=location["latitude"],
            longitude=location["longitude"],
            current_stress_level=bucket
        )
        db.add(farmer)
        db.commit()
        db.refresh(farmer)
    else:
        farmer.village_name = village
        farmer.crop_name = crop
        farmer.current_stress_level = bucket
        db.commit()

    alert = Alert(
        farmer_id=farmer.id,
        ndvi=satellite["ndvi"],
        ndwi=satellite["ndwi"],
        stress_level=bucket,
        stress_score=score,
        weather_summary=f"Rain in {weather['days_until_meaningful_rain']} days",
        alert_message_hindi=message["hindi"],
        is_reliable=satellite["is_reliable"]
    )
    db.add(alert)
    db.commit()

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

@app.get("/api/farmers")
def get_farmers(db: Session= Depends(get_db)):
    farmers=db.query(Farmer).all()
    print(f"DEBUG: /api/farmers query returned {len(farmers)} farmers")

    result=[]
    for f in farmers:
        result.append({
            "id":f.id,
            "phone_number":f.phone_number,
            "village_name":f.village_name,
            "crop_name":f.crop_name,
            "latitude":f.latitude,
            "longitude":f.longitude,
            "stress_level":f.current_stress_level,
            "registered_at": f.registered_at.isoformat() if f.registered_at else None
        })

    return {"farmers":result, "total":len(result)}

@app.get('/api/stats')
def get_stats(db: Session= Depends(get_db)):
    total_farmers=db.query(Farmer).count()

    low=db.query(Farmer).filter(Farmer.current_stress_level=='low').count()
    moderate=db.query(Farmer).filter(Farmer.current_stress_level=='moderate').count()
    high=db.query(Farmer).filter(Farmer.current_stress_level== 'high').count()
    critical=db.query(Farmer).filter(Farmer.current_stress_level=='critical').count()

    today=date.today()
    all_alerts=db.query(Alert).all()
    alerts_today=[a for a in all_alerts if a.created_at.date()==today]

    return{
        "total_farmers":total_farmers,
        "by_stress_level":{
            "low":low,
            "moderate":moderate,
            "high":high,
            "critical":critical
        },
        "alerts_today":len(alerts_today)
    }

@app.delete("/api/farmers/{farmer_id}")
def delete_farmer(farmer_id: int, db: Session = Depends(get_db)):
    farmer = db.query(Farmer).filter(Farmer.id == farmer_id).first()

    if farmer is None:
        return {"error": f"No farmer found with id {farmer_id}"}

    db.query(Alert).filter(Alert.farmer_id == farmer_id).delete()
    db.delete(farmer)
    db.commit()

    return {"message": f"Farmer {farmer_id} deleted successfully"}