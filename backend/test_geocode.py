from services.geocoder import get_coordinates

result = get_coordinates("Chitrakoot")
print(result)

result2 = get_coordinates("SomeRandomVillageXYZ")
print(result2)