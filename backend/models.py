from sqlalchemy import Column, Integer, String, Float, DateTime, ForeignKey, Boolean
from sqlalchemy.orm import relationship
from datetime import datetime
from database import Base

class Farmer(Base):
    __tablename__ = "farmers"

    id = Column(Integer, primary_key=True, index=True)
    phone_number = Column(String, unique=True, index=True)
    farmer_name = Column(String, nullable=True)
    village_name = Column(String)
    crop_name = Column(String)
    latitude = Column(Float)
    longitude = Column(Float)
    current_stress_level = Column(String, default="unknown")
    registered_at = Column(DateTime, default=datetime.utcnow)
    last_alert_at = Column(DateTime, nullable=True)

    alerts = relationship("Alert", back_populates="farmer")

class Alert(Base):
    __tablename__ = "alerts"

    id = Column(Integer, primary_key=True, index=True)
    farmer_id = Column(Integer, ForeignKey("farmers.id"))
    ndvi = Column(Float)
    ndwi = Column(Float)
    stress_level = Column(String)
    stress_score = Column(Integer)
    weather_summary = Column(String, nullable=True)
    alert_message_hindi = Column(String)
    is_reliable = Column(Boolean, default=True)
    created_at = Column(DateTime, default=datetime.utcnow)

    farmer = relationship("Farmer", back_populates="alerts")