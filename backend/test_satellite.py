# from services.satellite import get_satellite_indices, analyze_satellite

# raw = get_satellite_indices(25.1979, 80.8322)
# summary = analyze_satellite(raw)
# print(summary)

# from services.satellite import check_catalog

# result = check_catalog(25.1979, 80.8322)
# print(result)

# from services.stress_engine import calculate_stress

# satellite = {"ndvi": 0.751, "ndwi": -0.666}
# weather = {"days_until_meaningful_rain": 0, "max_temp_next_3_days_c": 32.3}

# result = calculate_stress(satellite, weather, "wheat")
# print(result)

from services.stress_engine import calculate_stress, generate_message

satellite = {"ndvi": 0.751, "ndwi": -0.666}
weather = {"days_until_meaningful_rain": 0, "max_temp_next_3_days_c": 32.3}

level = calculate_stress(satellite, weather, "wheat")
message = generate_message(level, "Chitrakoot", weather)

print(level)
print(message)