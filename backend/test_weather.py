from services.weather import get_weather_forecast, analyze_forecast

raw = get_weather_forecast(25.1979, 80.8322)
summary = analyze_forecast(raw)
print(summary)