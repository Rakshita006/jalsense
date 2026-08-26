from database import SessionLocal
from models import Farmer, Alert
from datetime import date

db = SessionLocal()

farmers = db.query(Farmer).all()
alerts = db.query(Alert).all()

print(f"Total farmers: {len(farmers)}")
for f in farmers:
    print(f"  - {f.phone_number} | {f.village_name} | {f.crop_name} | stress: {f.current_stress_level}")

print(f"\nTotal alerts: {len(alerts)}")
for a in alerts:
    print(f"  - farmer_id={a.farmer_id} | created_at={a.created_at} | today={date.today()}")

db.close()