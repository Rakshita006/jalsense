from fastapi import FastAPI 

app=FastAPI()

@app.get('/')
def read_root():
  return {'message':'Jalsense backend is running'}

@app.get('/predict')
def predict(village: str, crop: str):
  return{
    'village': village,
    'crop': crop,
    "stress_level": "high",
     "stress_score": 0.78,
      "days_until_critical": 5,
      "irrigate_by": "Tuesday",
       "alert_text_hindi": "Aapke khet mein agle 5 din mein pani ki kami ho sakti hai. Mangalwar tak sinchai karein."
  
  }