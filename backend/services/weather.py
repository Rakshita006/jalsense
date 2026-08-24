import requests

def get_weather_forecast(latitude, longitude):
    url = "https://api.open-meteo.com/v1/forecast"
    params = {
        "latitude": latitude,
        "longitude": longitude,
        "daily": "precipitation_sum,temperature_2m_max,temperature_2m_min",
        "timezone": "Asia/Kolkata",
        "forecast_days": 10
    }

    response = requests.get(url, params=params)
    data = response.json()

    return data

def analyze_forecast(forecast_data):
    daily=forecast_data['daily']
    dates=daily['time']
    rain=daily['precipitation_sum']
    max_temps=daily['temperature_2m_max']

    total_rain_7_days=sum(rain[:7])
    max_temp_3_days=max(max_temps[:3])

    days_until_rain=None
    for i,amount in enumerate(rain):
        if amount>=5:
            days_until_rain=i 
            break
    return {
        "total_rain_next_7_days_mm": round(total_rain_7_days, 1),
        "max_temp_next_3_days_c": max_temp_3_days,
        "days_until_meaningful_rain": days_until_rain
    }