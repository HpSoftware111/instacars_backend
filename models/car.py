from pydantic import BaseModel
from sqlalchemy import TIMESTAMP, Boolean, Column, DateTime, Integer, Numeric, String, Text
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.dialects.postgresql import JSONB

Base = declarative_base()

class Car(Base):
    __tablename__ = 'car_v2'
    id = Column(String, primary_key=True)
    vin = Column(String, nullable=True)
    heading = Column(String, nullable=True)
    price = Column(Numeric, nullable=True)
    miles = Column(Integer, nullable=True)
    msrp = Column(Numeric, nullable=True)
    data_source = Column(String, nullable=True)
    vdp_url = Column(String, nullable=True)
    carfax_1_owner = Column(Boolean, nullable=True)
    carfax_clean_title = Column(Boolean, nullable=True)
    exterior_color = Column(String, nullable=True)
    interior_color = Column(String, nullable=True)
    base_ext_color = Column(String, nullable=True)
    dom = Column(Integer, nullable=True)
    dom_180 = Column(Integer, nullable=True)
    dom_active = Column(Integer, nullable=True)
    dos_active = Column(Integer, nullable=True)
    seller_type = Column(String, nullable=True)
    inventory_type = Column(String, nullable=True)
    stock_no = Column(String, nullable=True)
    last_seen_at_date = Column(DateTime, nullable=True)
    scraped_at_date = Column(DateTime, nullable=True)
    first_seen_at_date = Column(DateTime, nullable=True)
    first_seen_at_source_date = Column(DateTime, nullable=True)
    first_seen_at_mc_date = Column(DateTime, nullable=True)
    ref_price = Column(Numeric, nullable=True)
    price_change_percent = Column(Numeric, nullable=True)
    ref_price_dt = Column(Integer, nullable=True)
    ref_miles = Column(Integer, nullable=True)
    ref_miles_dt = Column(Integer, nullable=True)
    source = Column(String, nullable=True)
    in_transit = Column(Boolean, nullable=True)
    financing_options = Column(JSONB, nullable=True)
    media = Column(JSONB, nullable=True)
    dealer = Column(JSONB, nullable=True)
    build = Column(JSONB, nullable=True)
    links = Column(JSONB, nullable=True)
    extra = Column(JSONB, nullable=True)
    car_location = Column(JSONB, nullable=True)

    def to_dict_for_agent(self):
      return {
          "id": self.id,
          "vin": self.vin,
          "heading": self.heading,
          "price": float(self.price) if self.price is not None else None,
          "miles": self.miles,
          "msrp": float(self.msrp) if self.msrp is not None else None,
          "data_source": self.data_source,
          "vdp_url": self.vdp_url,
          "carfax_1_owner": self.carfax_1_owner,
          "carfax_clean_title": self.carfax_clean_title,
          "exterior_color": self.exterior_color,
          "interior_color": self.interior_color,
          "base_ext_color": self.base_ext_color,
          "dom": self.dom,
          "dom_180": self.dom_180,
          "dom_active": self.dom_active,
          "dos_active": self.dos_active,
          "seller_type": self.seller_type,
          "inventory_type": self.inventory_type,
          "stock_no": self.stock_no,
          "last_seen_at_date": self.last_seen_at_date.isoformat() if self.last_seen_at_date else None,
          "scraped_at_date": self.scraped_at_date.isoformat() if self.scraped_at_date else None,
          "first_seen_at_date": self.first_seen_at_date.isoformat() if self.first_seen_at_date else None,
          "first_seen_at_source_date": self.first_seen_at_source_date.isoformat() if self.first_seen_at_source_date else None,
          "first_seen_at_mc_date": self.first_seen_at_mc_date.isoformat() if self.first_seen_at_mc_date else None,
          "ref_price": float(self.ref_price) if self.ref_price is not None else None,
          "price_change_percent": float(self.price_change_percent) if self.price_change_percent is not None else None,
          "ref_price_dt": self.ref_price_dt,
          "ref_miles": self.ref_miles,
          "ref_miles_dt": self.ref_miles_dt,
          "source": self.source,
          "in_transit": self.in_transit,
          "financing_options": self.financing_options,
          "media": self.media,
          "dealer": self.dealer,
          "build": self.build,
          "links": self.links,
          "extra": self.extra,
          "car_location": self.car_location
      }

class CarSummary(Base):
  __tablename__ = 'car_summary'
  id = Column(String, primary_key=True)
  summary = Column(Text)
  created_at = Column(TIMESTAMP)
  updated_at = Column(TIMESTAMP)

class CarAppointment(Base):
    __tablename__ = 'car_appointments'
    id = Column(String, primary_key=True)
    user_full_name = Column(String, nullable=False)
    email = Column(String, nullable=False)
    phone = Column(String, nullable=False)
    car_id = Column(String, nullable=False)
    appointment_date = Column(TIMESTAMP, nullable=False)

class AppointmentRequest(BaseModel):
    full_name: str
    email: str
    phone: str
    appointment_date: str

class FormRequest(BaseModel):
    type: str
    form: str
