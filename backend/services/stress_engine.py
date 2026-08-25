CROP_NDWI_BASELINE = {
    "wheat": {
        "healthy_min": -0.75,
        "stressed_max": -0.85
    },
    "rice": {
        "healthy_min": 0.10,
        "stressed_max": -0.10
    },
    "maize": {
        "healthy_min": -0.55,
        "stressed_max": -0.70
    },
    "chickpea": {
        "healthy_min": -0.65,
        "stressed_max": -0.80
    },
    "mustard": {
        "healthy_min": -0.60,
        "stressed_max": -0.75
    },
    "cotton": {
        "healthy_min": -0.50,
        "stressed_max": -0.65
    },
    "soybean": {
        "healthy_min": -0.45,
        "stressed_max": -0.60
    },
    "groundnut": {
        "healthy_min": -0.45,
        "stressed_max": -0.60
    },
    "pigeon_pea": {
        "healthy_min": -0.50,
        "stressed_max": -0.65
    },
    "sorghum": {
        "healthy_min": -0.55,
        "stressed_max": -0.70
    },
    "pearl_millet": {
        "healthy_min": -0.55,
        "stressed_max": -0.70
    },
    "finger_millet": {
        "healthy_min": -0.55,
        "stressed_max": -0.70
    },
    "barley": {
        "healthy_min": -0.65,
        "stressed_max": -0.80
    },
    "green_gram": {
        "healthy_min": -0.45,
        "stressed_max": -0.60
    },
    "black_gram": {
        "healthy_min": -0.45,
        "stressed_max": -0.60
    },
    "lentil": {
        "healthy_min": -0.60,
        "stressed_max": -0.75
    },
    "potato": {
        "healthy_min": -0.40,
        "stressed_max": -0.55
    },
    "sugarcane": {
        "healthy_min": -0.30,
        "stressed_max": -0.45
    },
    "tomato": {
        "healthy_min": -0.35,
        "stressed_max": -0.50
    },
    "onion": {
        "healthy_min": -0.45,
        "stressed_max": -0.60
    },
    "sunflower": {
        "healthy_min": -0.45,
        "stressed_max": -0.60
    },
}

DEFAULT_BASELINE = {
    "healthy_min": -0.60,
    "stressed_max": -0.75
}

def escalate(level):
    if level == "green":
        return "yellow"
    elif level == "yellow":
        return "red"
    return "red"

def calculate_stress(satellite, weather, crop):
  ndwi= satellite['ndwi']
  ndvi= satellite['ndvi']

  baseline= CROP_NDWI_BASELINE.get(crop.lower(), DEFAULT_BASELINE)
  healthy_min= baseline['healthy_min']
  stressed_max= baseline['stressed_max']


  if ndwi>=healthy_min:
    level="green"
  elif ndwi>=stressed_max:
    level="yellow"
  else:
    level='red'

  if ndvi<0.3:
    level=escalate(level)
  
  days_until_rain = weather["days_until_meaningful_rain"]
  max_temp = weather["max_temp_next_3_days_c"]

  if level == "yellow":
    if days_until_rain is not None and days_until_rain <= 3:
        level = "green"
    elif days_until_rain is None:
        level = escalate(level)
  if max_temp > 42:
    level = escalate(level)
  return level

def level_to_score_and_bucket(level, satellite, weather):
    base_scores = {"green": 20, "yellow": 50, "red": 75}
    score = base_scores[level]

    if level == "red" and (satellite["ndvi"] < 0.3 or weather["max_temp_next_3_days_c"] > 42):
        score = 90

    if score >= 80:
        bucket = "critical"
    elif score >= 60:
        bucket = "high"
    elif score >= 35:
        bucket = "moderate"
    else:
        bucket = "low"

    return score, bucket


def generate_message(bucket, village, weather):
    days_until_rain = weather["days_until_meaningful_rain"]

    if bucket == "low":
        hindi = f"Namaskar! Aapke {village} ke khet mein pani ki sthiti acchi hai. Abhi sinchai ki zaroorat nahi hai."
        english = f"Your field in {village} has adequate water. No irrigation needed right now."

    elif bucket == "moderate":
        hindi = f"Namaskar! Aapke {village} ke khet mein pani ki kami ho sakti hai. Jald hi sinchai ki taiyari karein."
        english = f"Your field in {village} may face water stress soon. Prepare to irrigate."

    elif bucket == "high":
        hindi = f"Namaskar! Aapke {village} ke khet mein pani ki kami ka risk zyada hai. Jald sinchai karein."
        english = f"Your field in {village} has a high risk of water stress. Irrigate soon."

    else:  # critical
        hindi = f"Namaskar! Aapke {village} ke khet mein pani ki gambhir kami hai! Turant sinchai karein."
        english = f"Critical water stress detected in your {village} field! Irrigate immediately."

    if days_until_rain is not None and days_until_rain <= 3 and bucket != "low":
        hindi += f" {days_until_rain} din mein baarish ki sambhavna hai."
        english += f" Rain expected in {days_until_rain} days."

    return {"hindi": hindi, "english": english}


        