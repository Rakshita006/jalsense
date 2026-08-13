import csv
import requests
import os

def load_local_villages():
  villages={}
  csv_path=os.path.join(os.path.dirname(__file__), '..', 'data', 'villages.csv')
  with open(csv_path, mode='r',encoding='utf-8') as file:
    reader = csv.DictReader(file)
    for row in reader:
      key=row['village_name'].strip().lower()
      villages[key]=row
  return villages

def get_coordinates(village_name, district=None):
  local_villages=load_local_villages()
  key=village_name.strip().lower()

  if key in local_villages:
    row=local_villages[key]
    return {
      'latitude':float(row['latitude']),
      'longitude':float(row['longitude']),
      'resolved_name':f"{row['village_name']}, {row['district']}, {row['state']}",
      'source':'local_csv'
    }

  query=f"{village_name}, {district}, India" if district else f'{village_name}, India'
  url='https://nominatim.openstreetmap.org/search'
  params={'q':query, 'format':'json', 'limit':1}
  headers={'User-Agent':'Jalsence-Hackathon-App'}

  response=requests.get(url, params=params, headers=headers)
  data=response.json()

  if len(data)>0:
    result=data[0]
    return {
      'latitude':float(result['lat']),
      'longitude': float(result['long']),
      'resolve_name': result['display_name'],
      'source':'nominatim'
    }
  
  return None