import os
import requests
from dotenv import load_dotenv

load_dotenv()

CLIENT_ID=os.getenv("SENTINEL_HUB_CLIENT_ID")
CLIENT_SECRET=os.getenv("SENTINEL_HUB_CLIENT_SECRET")

def get_access_token():
  url="https://identity.dataspace.copernicus.eu/auth/realms/CDSE/protocol/openid-connect/token"
  data={
    "grant_type":"client_credentials",
    "client_id":CLIENT_ID,
    "client_secret":CLIENT_SECRET
  }

  response= requests.post(url,data=data)
  token_data=response.json()

  return token_data["access_token"]

EVALSCRIPT_NDWI_NDVI = """
//VERSION=3
function setup() {
  return {
    input: [{ bands: ["B03", "B04", "B08", "dataMask"] }],
    output: [
      { id: "ndwi", bands: 1, sampleType: "FLOAT32"  },
      { id: "ndvi", bands: 1, sampleType: "FLOAT32"  },
      { id: "dataMask", bands: 1, sampleType: "FLOAT32"  }
    ]
  };
}

function evaluatePixel(sample) {
  let ndwi = (sample.B03 - sample.B08) / (sample.B03 + sample.B08);
  let ndvi = (sample.B08 - sample.B04) / (sample.B08 + sample.B04);
  return {
    ndwi: [ndwi],
    ndvi: [ndvi],
    dataMask: [sample.dataMask]
  };
}
"""

def get_satellite_indices(latitude, longitude):
    token = get_access_token()

    url = "https://sh.dataspace.copernicus.eu/statistics/v1"

    headers = {
        "Authorization": f"Bearer {token}",
        "Content-Type": "application/json"
    }

    delta = 0.002  # roughly 100m box around the point

    payload = {
        "input": {
            "bounds": {
                "bbox": [
                    longitude - delta,
                    latitude - delta,
                    longitude + delta,
                    latitude + delta
                ],
                "properties": {
                     "crs": "http://www.opengis.net/def/crs/OGC/1.3/CRS84"
                }
            },
            "data": [
                {
                    "type": "sentinel-2-l2a",
                    "dataFilter": {
                        "maxCloudCoverage": 50,
                        "mosaickingOrder": "leastCC"
                    }
                }
            ]
        },
        "aggregation": {
            "timeRange": {
               "from": "2026-01-01T00:00:00Z",
                "to": "2026-03-01T00:00:00Z"
            },
            "aggregationInterval": {"of": "P30D"},
            "resx": 0.0001,
            "resy": 0.0001,
            "evalscript": EVALSCRIPT_NDWI_NDVI
        }
    }

    response = requests.post(url, headers=headers, json=payload)
    return response.json()


def check_catalog(latitude, longitude, delta=0.002):
    token = get_access_token()
    url = "https://sh.dataspace.copernicus.eu/api/v1/catalog/1.0.0/search"

    headers = {
        "Authorization": f"Bearer {token}",
        "Content-Type": "application/json"
    }

    payload = {
        "collections": ["sentinel-2-l2a"],
        "datetime": "2026-01-01T00:00:00Z/2026-03-01T23:59:59Z",
        "bbox": [
            longitude - delta,
            latitude - delta,
            longitude + delta,
            latitude + delta
        ],
        "limit": 5
    }

    response = requests.post(url, headers=headers, json=payload)
    return response.json()

def analyze_satellite(raw_data):
    try:
        outputs = raw_data["data"][0]["outputs"]
        ndvi_mean = outputs["ndvi"]["bands"]["B0"]["stats"]["mean"]
        ndwi_mean = outputs["ndwi"]["bands"]["B0"]["stats"]["mean"]
        no_data_count = outputs["ndvi"]["bands"]["B0"]["stats"]["noDataCount"]
        sample_count = outputs["ndvi"]["bands"]["B0"]["stats"]["sampleCount"]

        cloud_percent = round((no_data_count / sample_count) * 100, 1) if sample_count > 0 else 100
        is_reliable = cloud_percent < 50

        return {
            "ndvi": round(ndvi_mean, 3),
            "ndwi": round(ndwi_mean, 3),
            "cloud_or_nodata_percent": cloud_percent,
            "is_reliable": is_reliable
        }
    except (KeyError, IndexError, TypeError):
        return None