from models.model import SuggestedCar
from sqlalchemy import create_engine
import os
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.orm import sessionmaker

engine = create_engine(os.getenv("DB_URL"))
SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)
Base = declarative_base()

def structured_car_search_output(output):
  if isinstance(output, dict):
        if "type" in output and "content" in output:
            return [output]
        else:
            return [{
                "type": "suggestion",
                "content": SuggestedCar(id)  # delete (id)
            }]
  elif isinstance(output, str):
      return [{
          "type": "message",
          "content": output
      }]
  else:
    return output
  

def filter_keys(car_data_list):
    keys_to_remove = {
        'links', 'dealer', 'mc_dealership', 'vin', 'data_source', 'last_seen_at', 'build', 'base_int_color', 'base_ext_color', 
        'carfax_1_owner', 'carfax_clean_title', 'exterior_color', 'interior_color', 'dom', 'dom_180', 'dom_active', 
        'seller_type', 'inventory_type', 'stock_no', "price_change_percent", "in_transit", "dos_active", "data_source"
        'last_seen_at', 'last_seen_at_date', 'scraped_at', 'scraped_at_date', 'first_seen_at', 'first_seen_at_date',
        "first_seen_at_source", "first_seen_at_source_name", "vdp_url", "source", "city", "state", "zip", "latitude", "longitude",
        "first_seen_at_source_date", "first_seen_at_mc", "first_seen_at_mc_date", "ref_price", "ref_miles", "ref_price_dt", "ref_miles_dt",
    }
    filtered_list = []

    for car_data in car_data_list:
        filtered_data = {key: value for key, value in car_data.items() if key not in keys_to_remove}
        
        # Handle the 'media' key specifically to limit 'photo_links' to only the first 1 images
        if 'media' in car_data and 'photo_links' in car_data['media']:
            filtered_data['media'] = car_data['media'].copy()  # Copy to avoid modifying original data
            filtered_data['media']['photo_links'] = car_data['media']['photo_links'][:1]  # Keep only first 1 images
            filtered_data['media']["photo_links_cached"] = []
        
        filtered_list.append(filtered_data)

    return filtered_list


from passlib.context import CryptContext

pwd_context = CryptContext(schemes=["bcrypt"], deprecated="auto")

