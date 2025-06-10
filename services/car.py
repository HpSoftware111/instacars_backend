import datetime
import requests
import uuid
import asyncio
import logging

from models.car import Car, CarAppointment
from sqlalchemy.orm import sessionmaker
from fastapi import HTTPException
from utils.util import engine

class CarService():
    def __init__(self):
      self._session = sessionmaker(autocommit=False, autoflush=False, bind=engine)

    def book_appointment(self, appointmentRequest, car_id):
      with self._session() as session:
        car_appointment = CarAppointment(
          id = str(uuid.uuid4()),
          user_full_name=appointmentRequest.full_name,
          email=appointmentRequest.email,
          phone=appointmentRequest.phone,
          car_id=car_id,
          appointment_date=appointmentRequest.appointment_date
        )
        session.add(car_appointment)
        session.commit()

    def book_appointment_confirmation_message(self, car_id, appointment_date):
      with self._session() as session:
        car = session.query(Car).filter(Car.id == car_id).first()
        car_heading = ""
        if car:
          car_heading = car.heading
        appointment_date = datetime.datetime.strptime(appointment_date, "%Y-%m-%dT%H:%M:%S.%fZ").strftime("%B %d, %Y")
        confirmation_message = f"Great! Your test drive for the {car_heading} has been successfully booked for {appointment_date}. 🚗✨ I'll send a confirmation email shortly!"
        user_confirmation_message = f"I have booked the test drive for {car_heading}."
        return {
          "assistant": confirmation_message,
          "user": user_confirmation_message
        }

    async def list_cars(self,base_url,params):
        try:
            response = requests.get(base_url,params=params)
            response.raise_for_status()
            cars =  response.json().get("listings")
            data = []
            for car in cars:
                data.append(self.custom_response(car))

            return data

        except requests.HTTPError as e:
            raise HTTPException(status_code=e.response.status_code,detail={str(e)})
        except requests.RequestException as e:
            raise HTTPException(status_code=500,detail=f"An error occoured while requesting: {str(e)}")
        except Exception as e:
            raise HTTPException(status_code=500,detail=f"Internal Server Error: {str(e)}")

    async def get_car_details_from_db(self, id):
        with self._session() as session:
            logging.info(f"DEBUG: searching car in DB: ")
            car = session.query(Car).filter(Car.id == id).first()
            car_data=car.to_dict_for_agent() if car else None
            return car_data

    async def car_details_from_marketcheck(self,base_url,params):
        logging.info(f"DEBUG: marketcheck api called with params: {params}")
        try:
            response = requests.get(base_url,params=params)
            response.raise_for_status()
            car = response.json()
            asyncio.create_task(asyncio.to_thread(self.save_cars_in_db, [car]))
            return self.custom_response(car)
        except requests.HTTPError as e:
            raise HTTPException(status_code=e.response.status_code,detail={str(e)}) 
        except requests.RequestException as e:
            raise HTTPException(status_code=500,detail=f"An error occoured while requesting: {str(e)}")
        except Exception as e:
            raise HTTPException(status_code=500,detail=f"Internal Server Error: {str(e)}")

    async def list_facets(self,base_url,params):
        try:
            req = requests.Request('GET',base_url,params=params).prepare()
            logging.info(f"Requesting: {req.url}")
            response = requests.get(base_url,params=params)
            response.raise_for_status()
            return self.custom_response_facets(response.json())
        except requests.HTTPError as e:
            raise HTTPException(status_code=e.response.status_code,detail={str(e)}) 
        except requests.RequestException as e:
            raise HTTPException(status_code=500,detail=f"An error occoured while requesting: {str(e)}")
        except Exception as e:
            raise HTTPException(status_code=500,detail=f"Internal Server Error: {str(e)}")

    def custom_response_facets(self, input_data):
        response = {
            "num_found": input_data.get("num_found", 0),
            "facets": {}
        }

        # Define desired filters
        desired_fuel_types = {"Electric", "Diesel", "Compressed Natural Gas"}
        desired_transmissions = {"Automatic", "Manual"}
        desired_body_types = {"SUV", "Pickup", "Sedan", "Minivan", "Coupe"}
        desired_colors = {"Black", "White", "Gray", "Blue", "Red","silver","green","Brown","Agate Black Metallic","Obsidian Black Metallic","Carbonized Grey Metallic","other"}  # Selected popular colors

        # Copy and filter facets
        for facet_key, facet_list in input_data.get("facets", {}).items():
            if facet_key == "fuel_type":
                # Filter fuel_type facet based on desired types
                response["facets"][facet_key] = [
                    item for item in facet_list if item["item"] in desired_fuel_types
                ]
            elif facet_key == "transmission":
                # Filter transmission facet based on desired types
                response["facets"][facet_key] = [
                    item for item in facet_list if item["item"] in desired_transmissions
                ]
            elif facet_key == "body_type":
                # Filter body_type facet based on desired types
                response["facets"][facet_key] = [
                    item for item in facet_list if item["item"] in desired_body_types
                ]
            elif facet_key == "exterior_color":
                # Filter exterior_color facet based on desired colors
                response["facets"][facet_key] = [
                    item for item in facet_list if item["item"] in desired_colors
                ]
            else:
                # Copy other facets as-is
                response["facets"][facet_key] = facet_list

        return response

    def save_cars_in_db(self, cars):
      with self._session() as session:
        for car_data in cars:
          # Check if car already exists by VIN
          existing_car = session.query(Car).filter(Car.id == car_data.get("id")).first()
          
          if existing_car:
            # Update existing car
            for key, value in car_data.items():
              setattr(existing_car, key, value)
          else:
            # Create new car
            # Filter car_data to only include columns that exist in Car model
            valid_columns = Car.__table__.columns.keys()
            filtered_car_data = {k: v for k, v in car_data.items() if k in valid_columns}
            new_car = Car(**filtered_car_data)
            session.add(new_car)
          logging.info(f"car saved: {car_data.get('id')}")
          session.commit()

    def custom_response(self,input_data):
        return {
            "_id": input_data.get("id"),
            "badge": {
                "badgeType": "great",  # This might need a condition or lookup
                "marketValue": f"${input_data.get('price', 0) - input_data.get('msrp',0)} BELOW MARKET",  # Adjust as needed
                "marketDiff": input_data.get('price', 0) - input_data.get('msrp', 0),
                "msrpValue": input_data.get('msrp', None),
            },
            "carfax": input_data.get("vdp_url"),
            "created_date": input_data.get("scraped_at_date"),
            "dealScore": input_data.get("dom", 0),  # Or another score-related field
            "dealer": {
                "name": input_data.get('dealer', {}).get("name"),
                "imgUrl": input_data.get('media', {}).get("photo_links", []),  # First image
                "phone": input_data.get('dealer', {}).get("phone"),
                "address": f"{input_data.get('dealer', {}).get('street')}, {input_data.get('dealer', {}).get('city')}, {input_data.get('dealer', {}).get('state')}",
            },
            "dealerLocation": {
                "type": "Point",
                "coordinates": [
                    float(input_data.get('dealer', {}).get('longitude', 0)),
                    float(input_data.get('dealer', {}).get('latitude', 0))
                ]
            },
            "dealerLocationDetails": {
                "AddressNumber": input_data.get('dealer', {}).get("street"),
                "Country": "US",  # Adjust as necessary
                "Geometry": {
                    "Point": [
                        float(input_data.get('dealer', {}).get('longitude', 0)),
                        float(input_data.get('dealer', {}).get('latitude', 0))
                    ]
                },
                "Interpolated": True,  # Adjust logic as necessary
                "Label": f"{input_data.get('dealer', {}).get('street')}, {input_data.get('dealer', {}).get('city')}, {input_data.get('dealer', {}).get('state')}",
                "Municipality": input_data.get('dealer', {}).get("city"),
                "PostalCode": input_data.get('dealer', {}).get("zip"),
                "Region": input_data.get('dealer', {}).get("state"),
                "Street": input_data.get('dealer', {}).get("street"),
                "SubRegion": None  # Adjust if necessary
            },
            "desc": input_data.get("heading"),
            "features": [
                f"{input_data.get('build', {}).get('engine_size')}L {input_data.get('build', {}).get('engine_block')} Engine",
                f"{input_data.get('build', {}).get('transmission')}",
                f"{input_data.get('build', {}).get('drivetrain')}",
                
            ],
            "location": {
                "city": input_data.get('dealer', {}).get("city"),
                "province": input_data.get('dealer', {}).get("state")
            },
            "media": {
                "images": input_data.get('media', {}).get("photo_links", [])
            },
            "mileageStatus": "new" if input_data.get("miles") == 0 else "used",
            "name": input_data.get("heading"),
            "price": input_data.get("price"),
            "sellerType": input_data.get("seller_type"),
            "specs": {
                "kilometres": (input_data.get("miles") or 0) * 1.60934,
                "status": input_data.get("inventory_type"),
                "trim": input_data.get('build', {}).get("trim"),
                "body-type": input_data.get('build', {}).get("body_type"),
                "engine": f"{input_data.get('build', {}).get('engine_size')}L {input_data.get('build', {}).get('engine_block')}",
                "cylinder": input_data.get('build', {}).get("cylinders"),
                "transmission": input_data.get('build', {}).get("transmission"),
                "drivetrain": input_data.get('build', {}).get("drivetrain"),
                "stock-number": input_data.get("stock_no"),
                "exterior-colour": input_data.get('build', {}).get("exterior_color"),
                "interior-colour": input_data.get('build', {}).get("interior_color"),
                "passengers": input_data.get('build', {}).get("std_seating"),
                "doors": input_data.get('build', {}).get("doors"),
                "fuel-type": input_data.get('build', {}).get("fuel_type"),
                "city-fuel-economy": None,  # Missing data?
                "hwy-fuel-economy": None   # Missing data?
            },
            "updated_date": input_data.get("last_seen_at_date"),
            "url": input_data.get("vdp_url"),
            "vehicle": {
                "make": input_data.get('build', {}).get("make"),
                "model": input_data.get('build', {}).get("model")
            },
            "vehicleAge": max(0, 2024 - int(input_data.get('build', {}).get("year", 2024))),
            "year": input_data.get('build', {}).get("year")
        }
