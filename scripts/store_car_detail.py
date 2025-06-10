from datetime import datetime
import logging
import os
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker

from agents.car_detail_agent import CarDetailAgent
from data.car_list import car_list
from models.car import Car, CarSummary

def insert_cars_into_db():
  DATABASE_URL = os.getenv("DB_URL")
  engine = create_engine(DATABASE_URL)
  Session = sessionmaker(autocommit=False, autoflush=False, bind=engine)
  session = Session()

  for car in car_list:
    new_car = Car(
      id=car.get('id'),
      vin=car.get('vin'),
      heading=car.get('heading'),
      price=car.get('price'),
      msrp=car.get('msrp'),
      data_source=car.get('data_source'),
      vdp_url=car.get('vdp_url'),
      carfax_1_owner=car.get('carfax_1_owner'),
      carfax_clean_title=car.get('carfax_clean_title'),
      exterior_color=car.get('exterior_color'),
      interior_color=car.get('interior_color'),
      base_int_color=car.get('base_int_color'),
      base_ext_color=car.get('base_ext_color'),
      dom=car.get('dom'),
      dom_180=car.get('dom_180'),
      dom_active=car.get('dom_active'),
      dos_active=car.get('dos_active'),
      seller_type=car.get('seller_type'),
      inventory_type=car.get('inventory_type'),
      stock_no=car.get('stock_no'),
      last_seen_at=car.get('last_seen_at'),
      last_seen_at_date=car.get('last_seen_at_date'),
      scraped_at=car.get('scraped_at'),
      scraped_at_date=car.get('scraped_at_date'),
      first_seen_at=car.get('first_seen_at'),
      first_seen_at_date=car.get('first_seen_at_date'),
      first_seen_at_source=car.get('first_seen_at_source'),
      first_seen_at_source_date=car.get('first_seen_at_source_date'),
      first_seen_at_mc=car.get('first_seen_at_mc'),
      first_seen_at_mc_date=car.get('first_seen_at_mc_date'),
      ref_price=car.get('ref_price'),
      price_change_percent=car.get('price_change_percent'),
      ref_price_dt=car.get('ref_price_dt'),
      ref_miles=car.get('ref_miles'),
      ref_miles_dt=car.get('ref_miles_dt'),
      source=car.get('source'),
      in_transit=car.get('in_transit'),
      media=car.get('media'),
      dealer=car.get('dealer'),
      build=car.get('build'),
      links=car.get('links'),
    )
    session.add(new_car)
    session.commit()
  
  session.close()

async def store_car_summary():
  DATABASE_URL = os.getenv("DB_URL")
  engine = create_engine(DATABASE_URL)
  Session = sessionmaker(autocommit=False, autoflush=False, bind=engine)
  session = Session()
  cda = CarDetailAgent()
  for car in car_list:
    summary = await cda.generate_car_summary(car)
    new_summary = CarSummary(
      id=car.get('id'),
      summary=str(summary),
      created_at=datetime.now(),
      updated_at=datetime.now()
    )
    session.add(new_summary)
    session.commit()
  session.close()