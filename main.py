import os
import asyncio
import logging, json, uuid
import requests
import time
import boto3

from services.car import CarService
from services.form import FormService
from services.sendEmail import EmailService
from fastapi import FastAPI, Query, WebSocket, WebSocketDisconnect, Body, HTTPException, Request, status, Depends, File, UploadFile, Header
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles
from fastapi.responses import JSONResponse
from agents.orchestation_agent import OrchestationAgent
from agents.car_search_agent import CarSearchAgent
from agents.general_agent import GeneralAgent
from agents.car_detail_agent import CarDetailAgent
from services.chat import ChatService

from models.model import CarDetailResponse, CarOptionsResponse, CarSearchResponse, ChatHistory, ChatMessage, Response
from scripts.store_car_detail import store_car_summary
from models.car import AppointmentRequest, FormRequest
from models import chat
from typing import List,Optional
from dotenv import load_dotenv
import os
from sqlalchemy.orm import Session
# from  . import database,  timedelta
# --------- modules for auth start ----------->
from utils import util as database
from models.user import User
from models import  user
from utils.auth import verify_password, create_access_token, get_password_hash, verify_token, get_email_from_token
from datetime import datetime, timedelta
from jose import JWTError, jwt
from pydantic import EmailStr
from fastapi.security import OAuth2PasswordBearer
from sqlalchemy import create_engine, text
from schema import schemas
from models.verifiedlink import VerificationToken
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials
#--------- modules for auth end ----------->
# -----------google auth ------------------>
# from authlib.integrations.starlette_client import OAuth
#  Email settings:
load_dotenv()
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
security = HTTPBearer()
ALGORITHM =os.getenv("JWT_TOKEN_ALGORITHM")
SECRET_KEY = os.getenv("JWT_SECRET_KEY")
chat_history = {}
car_details_history={}
filter_history={}
# reset password tokens
reset_tokens = {}
# for token verification
oauth2_scheme = OAuth2PasswordBearer(tokenUrl="login")  # ✅ declare this!
# file upload setting
UPLOAD_DIR = "uploads/avatars"
os.makedirs(UPLOAD_DIR, exist_ok=True)
# 

def get_db():
    db = database.SessionLocal()
    try:
        yield db
    finally:
        db.close()


def store_chat_messages(chat_id, role, message,user_id: Optional[str] = None):
  #  print user_id for testing 
  if chat_id not in chat_history:
    chat_history[chat_id] = ChatHistory(messages=[])
  chat_history[chat_id].messages.append(ChatMessage(role=role, content=message))
  asyncio.create_task(asyncio.to_thread(ChatService().store_chat_messages_db, chat_id, {"role": role, "content": message}, user_id))

def store_car_details_messages(chat_id,role,message):
  if chat_id not in car_details_history:
    car_details_history[chat_id] = ChatHistory(messages=[])
  car_details_history[chat_id].messages.append(ChatMessage(role=role,content=message))
  asyncio.create_task(asyncio.to_thread(ChatService().store_chat_messages_db, chat_id, {"role": role, "content": message}, user_id))

def clear_chat_messages(chat_id):
  if chat_id in chat_history:
    del chat_history[chat_id]

def initialize_chat_history(chat_id):
  if chat_id not in chat_history:
    chat_history[chat_id] = ChatHistory(messages=[])

def initialize_car_details_history(chat_id):
  if chat_id not in car_details_history:
    car_details_history[chat_id] = ChatHistory(messages=[])

def initialize_filter_history(chat_id):
  if chat_id not in filter_history:
    filter_history[chat_id] = {}
    
app = FastAPI()

origins = ["*"]

app.add_middleware(
  CORSMiddleware,
  allow_origins=origins,
  allow_credentials=True,
  allow_methods=["*"],
  allow_headers=["*"],
)

@app.get("/")
def test_api():
  return "I'm up."

@app.websocket("/chats/{chat_id}")
async def websocket_endpoint(websocket: WebSocket, chat_id: str, token: Optional[str] = Query(None), db: Session = Depends(get_db)):
  
  # print("websocket time start..............")
  await websocket.accept()
  oa = OrchestationAgent()
  csa = CarSearchAgent()
  ga = GeneralAgent()
  cda = CarDetailAgent()

  user_id = None
  if token:
    try:
      email = get_email_from_token(token)
      user = get_user_by_email(email, db)
      if user:
        user_id = str(user.id)
    except Exception as e:
      logging.warning(f"Token validation failed: {str(e)}")
      # Continue without user_id
  
  logging.info(f"Conversation started for chat_id: {chat_id}")
  is_introduced = True
  while True:
    try:
      data = await websocket.receive_text()
      try:
        jsonData = json.loads(data)
      except json.JSONDecodeError as json_err:
        logging.error(f"JSON decode error: {json_err}")
        await websocket.send_text(json.dumps({"type": "error", "message": "Unable to process your queries"}))
        continue

      if jsonData['type'] == "ping_pong":
        await websocket.send_text(json.dumps({"type": "ping_pong", "message": "pong"}))
      else:
        start_time = time.time()
        # initialize the chat_history if chat_id does not exist
        initialize_chat_history(chat_id)
        initialize_filter_history(chat_id)
        initialize_car_details_history(chat_id)
        user_message = jsonData['text']
        if isinstance(jsonData.get("filter"), dict):
          filter_history[chat_id]=jsonData.get("filter")
        # logging.info(f"User message: {user_message}")

        summary = await oa.generate_conversation_summary(chat_history[chat_id])
        # /**********
        agent_type = await oa.determine_agent_to_call(store_chat_messages, summary, user_message, {"session_id": chat_id})

        if agent_type == "car_search_agent":
          # logging.info("calling car search agent")
          suggested_cars = []
          conversation_start_time = time.time()
          response = await csa.conversation(store_chat_messages, filter_history,chat_history[chat_id], message = user_message, session={"session_id": chat_id}, user_id=user_id)
          conversation_time = time.time() - conversation_start_time
          logging.info(f"⏱️ Time taken for csa.conversation: {conversation_time:.4f} sec")
          if isinstance(response, list) and all(isinstance(item, CarSearchResponse) for item in response):
            for msg in response:
              if msg.type=="message":
                if isinstance(msg.content, str) and "I'm Kaia" in msg.content:
                  if is_introduced:
                    continue
                  else:
                    is_introduced = True

                resp = {
                  "type": "message",
                  "message": {"type": "message", "content": msg.content},
                  "is_last": False
                }
              elif msg.type=="suggestion":
                suggested_cars = msg.content
                resp = {
                  "type": "suggestion",
                  "message": {"type": "suggestion", "content": [car.dict() for car in suggested_cars]},
                  "is_last": False
                }
              else:
                resp = {
                  "type": "message",
                  "message": {"type": "other", "content": msg.content},
                  "is_last": False
                }
              if msg == response[-1]:
                resp["is_last"] = True

              end_time = time.time() - start_time
              logging.info(f"⏱️ Time taken for total: {end_time:.4f} sec")
              await websocket.send_text(f"{json.dumps(resp)}")
              await asyncio.sleep(1.5)

          response = await csa.conversation_to_get_options(
            suggested_cars=[car.dict() for car in suggested_cars],
            chat_history=chat_history,
            message=user_message,
          )

          if isinstance(response, CarOptionsResponse):
            if response.type == "options":
                resp = {
                "type": "message",
                "message": {"type": "options", "content": response.content},
                "is_last": True
              }
            else:
              resp = {
                "is_last": True
              }

            await websocket.send_text(f"{json.dumps(resp)}")
            await asyncio.sleep(1)

        elif agent_type == "general_agent":
          logging.info("calling general agent")
          response = await ga.conversation(store_chat_messages, chat_history[chat_id], message= user_message, session={"session_id": chat_id}, user_id=user_id)
          if isinstance(response, Response):
            for msg in response.messages:
              resp = {
                "type": "message",
                "message": {"type": "message", "content": msg},
                "is_last": False
              }

              if msg == response.messages[-1]:
                resp["is_last"] = True

              await websocket.send_text(f"{json.dumps(resp)}")
              await asyncio.sleep(2)
        elif agent_type == "car_details_agent":
          logging.info(f"car details history: {car_details_history[chat_id]}")
          logging.info("calling car details agent")
          user_message = jsonData["text"]
          metadata = jsonData.get("metadata")
          response = await cda.conversation(store_car_details_messages,chat_history = car_details_history[chat_id], message=user_message, car_id = metadata.get("car_id"),   user_id=user_id,   session ={"session_id": chat_id} )
          if isinstance(response, list) and all(isinstance(item, CarDetailResponse) for item in response):
            for msg in response:
              if msg.type=="message":
                if isinstance(msg.content, str) and "I'm Kaia" in msg.content:
                  if is_introduced:
                    continue
                  else:
                    is_introduced = True

                resp = {
                  "type": "message",
                  "message": {"type": "message", "content": msg.content},
                  "is_last": False
                }
              elif msg.type == "options":
                 resp = {
                  "type": "message",
                  "message": {"type": "options", "content": msg.content},
                  "is_last": False
                }
              else:
                resp = {
                  "type": "message",
                  "message": {"type": "other", "content": msg.content},
                  "is_last": False
                }
              if msg == response[-1]:
                resp["is_last"] = True

              logging.info(f"sending message: {resp}")
              await websocket.send_text(f"{json.dumps(resp)}")
              await asyncio.sleep(2.5)
        elif agent_type == "alert_user_to_select_a_car":
          resp = {
            "type": "message",
            "message": {"type": "message", "content": "Please select one of the cars from above for specs and other detailed information"},
            "is_last": True
          }

          await websocket.send_text(f"{json.dumps(resp)}")
        elif agent_type == "book_test_drive":
          # resp = {
          #   "type": "message",
          #   "message": {"type": "message", "content": "To finalize your test drive booking, please fill out this quick form with your details. 🚗✨ It will help us confirm your appointment and make sure everything is ready for your visit!"},
          #   "is_last": False
          # }
          # await websocket.send_text(f"{json.dumps(resp)}")
          # await asyncio.sleep(1)
          resp = {
            "type": "message",
            "message": {"type": "book_appointment", "content": ""},
            "is_last": True
          }
          await websocket.send_text(f"{json.dumps(resp)}")
        else:
          logging.info("agent not found")
          resp = {
            "type": "message",
            "message": {"type": "message", "content": "I don't know how to answer this. Please elaborate your message"},
            "is_last": True
          }
          await websocket.send_text(f"{json.dumps(resp)}")

    except WebSocketDisconnect:
      logging.info(f"WebSocket disconnected for chat_id: {chat_id}")
      response = {"type": "disconnected", "message": "Bot left the chat"}
      try:
        await websocket.send_text(json.dumps(response))
      except Exception as final_err:
        logging.error(f"Failed to send disconnect message: {final_err}")
      return
    except Exception as e:
      response = {"type": "error", "message": "error occurred. Try again."}
      await websocket.send_text(json.dumps(response))
      logging.error(f"Exception occurred: {e}")

@app.post("/chats")
async def create_chat(token: Optional[str] = Depends(oauth2_scheme), db: Session = Depends(get_db)):
  try:
    user_id = None
    if token:
      email = get_email_from_token(token)
      if email:
        user = get_user_by_email(email, db)
        if user:
          user_id = str(user.id)
  except Exception as e:
    # If token validation fails, continue without user_id
    pass
  
  id = str(uuid.uuid4())
  messages_data = []
  
  if user_id:
    messages = db.query(chat.ChatMessage).filter(chat.ChatMessage.user_id == user_id).all()
    # Build response messages list
    for message in messages:
      messages_data.append({
        "message_id": str(message.message_id),
        "chat_id": str(message.chat_id),        
        "message": message.message,
        "type": "message",
        "created_at": message.created_at.isoformat() if message.created_at else None
      })

  return JSONResponse(content={
      "message": "New chat created",
      "id": str(id),
      "chat_messages": messages_data
  })

@app.post("/chat_history")
async def create_chat( db: Session = Depends(get_db)):
  id = str(uuid.uuid4())
  messages = db.query(chat.ChatMessage).all()
  # If no messages found (optional check)
  if not messages:
      # Optional: You can raise an exception if needed
      raise HTTPException(status_code=404, detail="No messages found for this chat_id")
  target_id = id
  # Build response messages list
  messages_data = []
  for message in messages:
    #  if str(message.chat_id) == target_id:
    messages_data.append({
        "message_id": str(message.message_id),
        "chat_id": str(message.chat_id),        
        "message": message.message,
        "created_at": message.created_at.isoformat() if message.created_at else None
    })
  
  return JSONResponse(content={
      "message": "New chat created",
      "id": str(id),
      # "type":"",
      "chat_messages": messages_data
  })
@app.post("/car-details")
async def store_cars():
  await store_car_summary()

@app.post("/book-appointment/{id}")
async def book_test_drive(  id: str,  request: Request,  appointmentRequest: AppointmentRequest = Body(...), token: str = Depends(oauth2_scheme)):

  email = get_email_from_token(token)
 
  subject = "Book an apppointment"
  form_data_dict = appointmentRequest.model_dump()
  email_body = json.dumps(form_data_dict, indent=2)

  email_service = EmailService()
  email_service.send_email(recipient=form_data_dict.get("email"), subject=subject, body=email_body)
  try:
    session_id = request.headers.get("session-id")
    logging.info(session_id)
    car_service = CarService()
    car_service.book_appointment(car_id=id, appointmentRequest=appointmentRequest)
    message = car_service.book_appointment_confirmation_message(
      car_id=id, appointment_date=appointmentRequest.appointment_date
    )
    store_chat_messages(session_id, role="user", message=message.get("user"), user_id=user_id)
    store_chat_messages(session_id, role="assistant", message=message.get("assistant"), user_id=user_id)
    return JSONResponse(content={
          "type": "message",
          "message": {"type": "message", "content": message.get("assistant")},
          "is_last": True
        })
  except Exception as e:
    logging.error(f"Book a test drive failed: {str(e)}")
    raise HTTPException(status_code=400, detail=f"""
      I'm sorry, but it looks like booking the test drive could not be completed. 😕 Please try again or contact our support team for assistance.
    """)

@app.get("/filtering/cars")
async def filter_cars(
    condition : Optional[str] = Query(None), # either new, used or certified
    transmission: Optional[List[str]] = Query(None),
    fuel_type: Optional[List[str]]=Query(None),
    drivetrain: Optional[List[str]] = Query(None),
    body_type:Optional[List[str]] = Query(None),# suv, sedan, pickup, hatchback, coupe, wagon
    seller_type:Optional[List[str]] = Query(None), # franchise, independent
    min_year:Optional[int] = Query(None),
    max_year:Optional[int] = Query(None),
    doors:Optional[str] = Query(None),
    color:Optional[str] = Query(None),
    skip:int = Query(0, ge=0),
    limit: int = Query(1,ge=0, fe=0)
 ):
    host = os.getenv("MARKETCHECK_HOST")
    api_key = os.getenv("MARKETCHECK_API_KEY")

    if not host or not api_key:
        raise HTTPException(status_code=500,detail="API Credentials not Configured")

    base_url =  f"https://{host}/v2/search/car/active"
    # base_url = f"https://run.mocky.io/v3/97741b2b-2aaa-4ec5-9dd8-03d8a722f476"

    # default query parameters
    params = {
      "api_key": api_key,
      "include_relevent_links": "true",
      "start": skip,
      "rows": limit,
      "country": "CA"
    }
    # optional query parameters
    
    if min_year or max_year:
      min_year = min_year if min_year else 2005
      max_year = max_year if max_year else 2025
      years = list(range(min_year,max_year+1))
      params["year"]= ",".join(map(str,years))

    if condition:
        params["car_type"]=condition
    if body_type:
        params["body_type"]=",".join(body_type)

    if transmission:
        params["transmission"]=",".join(transmission)

    if fuel_type:
        params["fuel_type"]=",".join(fuel_type)

    if drivetrain:
        params["drivetrain"]=",".join(drivetrain)


    if color:
        params["exterior_color"]=",".join(color)

    if doors:
        params["doors"]=",".join(doors)

    if seller_type:
        params["dealer_type"]=",".join(seller_type)


    try:
        response = await CarService().list_cars(base_url=base_url,params=params)
        return JSONResponse(response)
    except Exception as e:
        raise e

@app.get("/detailed/{id}")
async def get_car_details(id:str):
  car_service = CarService()
  car_details = await car_service.get_car_details_from_db(id)
  if car_details is None:
    host = os.getenv("MARKETCHECK_HOST")
    api_key = os.getenv("MARKETCHECK_API_KEY")

    if not host or not api_key:
        raise HTTPException(status_code=500,detail="API Credentials not Configured")

    base_url = f"https://{host}/v2/listing/car/{id}"
    params = {
      "api_key": api_key,
    }
    try:
      response = await car_service.car_details_from_marketcheck(base_url=base_url,params=params)
      final_response = car_service.custom_response(response)
      return JSONResponse(final_response)
    except Exception as e:
      raise e
  else:
    response = car_service.custom_response(car_details)
    return JSONResponse(response)

@app.get("/count/options")
async def get_facets(
    condition : Optional[str] = Query(None), # either new, used or certified
    transmission: Optional[List[str]] = Query(None),
    fuel_type: Optional[List[str]]=Query(None),
    drivetrain: Optional[List[str]] = Query(None),
    body_type:Optional[List[str]] = Query(None),# suv, sedan, pickup, hatchback, coupe, wagon
    seller_type:Optional[List[str]] = Query(None), # franchise, independent
    min_year:Optional[int] = Query(None),
    max_year:Optional[int] = Query(None),
    doors:Optional[str] = Query(None),
    color:Optional[str] = Query(None),
):
    host = os.getenv("MARKETCHECK_HOST")
    api_key = os.getenv("MARKETCHECK_API_KEY")

    if not host or not api_key:
        raise HTTPException(status_code=500,detail="API Credentials not Configured")

    base_url = f"https://{host}/v2/search/car/active"

    params = {
      "api_key": api_key,
      "country": "CA", 
      "start": "0",
      "rows": "0",
    }

    facets = ["car_type","transmission","fuel_type","drivetrain","body_type","doors","exterior_color"]
    params["facets"] = ",".join(facets)

    # optional query parameters

    if min_year or max_year:
      min_year = min_year if min_year else 2005
      max_year = max_year if max_year else 2025
      years = list(range(min_year,max_year+1))
      params["year"]= ",".join(map(str,years))

    if condition:
        params["car_type"]=condition
    if body_type:
        params["body_type"]=",".join(body_type)

    if transmission:
        params["transmission"]=",".join(transmission)

    if fuel_type:
        params["fuel_type"]=",".join(fuel_type)

    if drivetrain:
        params["drivetrain"]=",".join(drivetrain)

    if color:
        params["exterior_color"]=",".join(color)

    if doors:
        params["doors"]=",".join(doors)

    if seller_type:
        params["dealer_type"]=",".join(seller_type)

    try:
        response = await CarService().list_facets(base_url=base_url,params=params)
        return response
    except Exception as e:
        raise e 

@app.post("/forms")
async def store_contact_form(
  req: Request,
  formRequest: FormRequest = Body(...)
):
  subject = formRequest.type

  try:
    # Try to parse formRequest.form as JSON
    form_data = formRequest.form
    if isinstance(form_data, str):
      form_data = json.loads(form_data)

    ip = req.headers.get("x-forwarded-for") or req.client.host
    response = await FormService().store_contact_form(formRequest, ip)
    email_service = EmailService()
    email_service.send_email(
      recipient=form_data.get("email"),
      subject=subject,
      body=form_data.get("message"),
    )

    return response
  except Exception as e:
    raise e

@app.get("/health")
async def health_check():
  return {"status":"healthy"}

@app.delete("/deleteone/{id}")
async def delete_contact_form_by_id(id:str):
  try:
    response = await FormService().delete_contact_form_by_id(id)
    return response
  except Exception as e:
    raise e

@app.post("/reCaptcha")
async def recaptha(req:Request):
  try:
    data = await req.json()
    token = data.get("token")
    secret = os.getenv("RECAPTCHA_SECRET")

    response = requests.post(
        "https://www.google.com/recaptcha/api/siteverify",
        params={
          'secret': secret,
          'response': token
        }
    )
    if response.ok:
      return response.json().get("success", False)
    return False
  except Exception as e:
    logging.error(f"Recaptcha failed: {str(e)}")
    return False

@app.post("/signup")
async def signup(user: schemas.UserCreate, db: Session = Depends(get_db)):
    # Check if the email already exists
    db_user = db.query(User).filter(User.email == user.email).first()
    if db_user:
        return {
            "detail": "Email already registered",
            "status": "warning"
        }
    # Validate password complexity (e.g., minimum length of 8 characters, contains numbers)
    if len(user.password) < 8:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Password must be at least 8 characters long",
        )
    
    if not any(char.isdigit() for char in user.password):
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Password must contain at least one digit",
        )
    
    if not any(char.isalpha() for char in user.password):
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Password must contain at least one letter",
        )

    # Hash the user's password
    hashed_password = get_password_hash(user.password)

    # Create the new user
    new_user = User(email=user.email, hashed_password=hashed_password, ai_data=False)
    db.add(new_user)
    db.commit()
    db.refresh(new_user)
    if new_user:
      #  Sending Email for SignIn
      # Create JWT token
      expiry = timedelta(minutes=3000)
      token = create_access_token(data={"sub": user.email}, expires_delta=expiry)
      #  Save token in Verification Token table  for one time verified link
      db_token = VerificationToken(token=token, email=user.email)
      db.add(db_token)
      db.commit()
      # 
      # Store token securely
      reset_tokens[token] = (user.email, datetime.utcnow() + expiry)
      # Create reset link
      frontend_url = os.getenv("DOMAIN_URL")
      signin_link = f"{frontend_url}/emailVerified?token={token}"
      print(signin_link)
      # Prepare email
      subject = "Welcome! Confirm Your Email to Get Started"
      body = (
          f"Hi,\n\n"
          f"Thank you for signing up! To complete your registration, please verify your email address by clicking the link below:\n\n"
          f"{signin_link}\n\n"
          f"This link will expire in 10 minutes for security reasons.\n\n"
          f"If you did not create this account, you can safely ignore this email."
      )
      email_service = EmailService()
      email_service.send_email( recipient = user.email, subject = subject, body = body)  
      # Sending email end 
      return JSONResponse(
          status_code=201,
          content={
              "status": "success",
              "message": "User created successfully",
              "user": {
                  "id": new_user.id,
                  "email": new_user.email,
              }
          }
      )
    else:
      raise HTTPException(status_code=400, detail="User creation failed")

@app.post("/signin")
async def signin(user: schemas.UserCreate, db: Session = Depends(get_db)):
    # Check if the user exists
    db_user = db.query(User).filter((User.email == user.email) & (User.is_active == True)& (User.is_verified == True)).first()
    if not db_user:
        raise HTTPException(status_code=404, detail="User not found")
    # Verify the password
    if not verify_password(user.password, db_user.hashed_password):
        raise HTTPException(status_code=401, detail="Incorrect password")
    # Create a JWT token
    access_token = create_access_token(data={"sub": db_user.email})
    return {"token": access_token}
@app.post("/reset-password")
async def reset_password(email: EmailStr = Body(..., embed=True), db: Session = Depends(get_db)):
    # Check if email exists in your user DB
    
    user = get_user_by_email(email,  db)  # Replace with actual logic
    if not user:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Email not found")

    # Create JWT token
    expiry = timedelta(minutes=300)
    token = create_access_token(data={"sub": email}, expires_delta=expiry)
    
    # Store token securely
    reset_tokens[token] = (email, datetime.utcnow() + expiry)

    # Create reset link
    frontend_url = os.getenv("DOMAIN_URL", "http://localhost:3000")
    print(frontend_url)
    reset_link = f"{frontend_url}/newPwd?token={token}"

    # Prepare email
    subject = "Password Reset Request"
    body = (
        f"Hi ,\n\n"
        f"Click the following link to reset your password:\n\n{reset_link}\n\n"
        f"This link will expire in 10 minutes.\n\n"
        f"If you did not request a password reset, please ignore this message."
    )

    # Send email
    print("Reset password URL:", reset_link)
    email_service = EmailService()
    email_service.send_email(email, subject, body)

    return {"msg": "Reset link sent if the email exists in our system"}

@app.post("/confirm-reset-password")
async def confirm_reset_password(
    payload: schemas.ConfirmResetRequest,
    db: Session = Depends(get_db)
):
    try:
        email = verify_token(payload.token)
        if not email:
            raise HTTPException(status_code=400, detail="Invalid token: missing subject")
    except JWTError:
        raise HTTPException(status_code=400, detail="Token is invalid or expired")

    user = get_user_by_email( email, db)
    if not user:
        raise HTTPException(status_code=404, detail="User not found")

    # Hash the new password
    hashed_password = get_password_hash(payload.new_password)

    # Update user's password
    user.hashed_password = hashed_password
    db.commit()

    return {"msg": "Password updated successfully"}
@app.post("/api/delete-search-data")
async def delete_search_data(data: schemas.AIDataUpdateRequest,token: str = Depends(oauth2_scheme),db: Session = Depends(get_db)):
    """
    Updates the user's AI data retention preference (on/off).
    """
    email = get_email_from_token(token)
    user = get_user_by_email(email, db)
    if not user:
        raise HTTPException(status_code=404, detail="User not found")

    try:
        user.ai_data = not data.ai_data
        db.commit()
        return {
            "success": True,
            "email": email,
            "type":"ai-data",
            "msg": f"AI data retention {'enabled' if user.ai_data else 'disabled'}."
        }
    except Exception:
        db.rollback()
        raise HTTPException(status_code=500, detail="Failed to update AI data setting")

@app.post("/api/delete-account")
async def delete_account(token: str = Depends(oauth2_scheme),    db: Session = Depends(get_db)):
    email = get_email_from_token(token)
    user = get_user_by_email(email, db)
    if not user:
        raise HTTPException(status_code=404, detail="User not found")

    user.is_active = False
    db.commit()  # No need for db.delete(user)

    return {"msg": f"Account deleted for {email}", "type":"delete"}

@app.post("/api/signout")
async def sign_out(token: str = Depends(oauth2_scheme)):
    email = get_email_from_token(token)

    # Optionally log the event, invalidate token, etc.

    return {"msg": f"Signed out {email}", "type":"signout"}
@app.post("/api/upload-avatar")
async def upload_avatar(    avatar: UploadFile = File(...),    Authorization: str = Header(...),    db: Session = Depends(get_db)):
    # Step 1: Get email from token
    token = Authorization.split(" ")[1]
    email = verify_token(token)
    if not email:
        raise HTTPException(401, detail="Invalid or missing token")

    # Step 2: Get user
    user = db.query(User).filter(User.email == email).first()
    if not user:
        raise HTTPException(404, detail="User not found")

    # Step 3: Save file
    ext = os.path.splitext(avatar.filename)[1]
    filename = f"{uuid.uuid4().hex}{ext}"
    file_path = os.path.join(UPLOAD_DIR, filename)

    with open(file_path, "wb") as f:
        content = await avatar.read()
        f.write(content)

    # Step 4: Update user avatar
    user.avatar_url = f"/{file_path}"
    db.commit()

    return {"message": "Avatar uploaded", "avatar_url": user.avatar_url}
@app.get("/me")
def get_user_info(
    Authorization: str = Header(...),
    db: Session = Depends(get_db)
):
    try:
        token = Authorization.replace("Bearer ", "")
        email = verify_token(token)
        if not email:
            raise HTTPException(status_code=401, detail="Invalid token")

        user = db.query(User).filter(User.email == email).first()
        if not user:
            raise HTTPException(status_code=404, detail="User not found")

        return {
            "email": user.email,
            "avatar_url": user.avatar_url,
            "ai_data": getattr(user, "ai_data", False),  # Optional field if it exists
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail="Server error")
app.mount("/uploads", StaticFiles(directory="uploads"), name="uploads")      

@app.post("/resend-verification")
async def resend_verification(request: schemas.EmailRequest, db: Session = Depends(get_db)):
    email = request.email

    # Find the user by email
    user = db.query(User).filter(User.email == email).first()
    if not user:
        raise HTTPException(status_code=404, detail="User not found")

    if user:
        return {"message": "User already verified"}
 #  Sending Email for SignIn
      # Create JWT token
    expiry = timedelta(minutes=3000)
    token = create_access_token(data={"sub": email}, expires_delta=expiry)
    #  Save token in Verification Token table  for one time verified link
    db_token = VerificationToken(token=token, email=email)
    db.add(db_token)
    db.commit()
    # 
    # Store token securely
    reset_tokens[token] = (email, datetime.utcnow() + expiry)
    # Create reset link
    frontend_url = os.getenv("DOMAIN_URL")
    signin_link = f"{frontend_url}/emailVerified?token={token}"
    print(signin_link)
    # Prepare email
    subject = "Welcome! Confirm Your Email to Get Started"
    body = (
        f"Hi,\n\n"
        f"Thank you for signing up! To complete your registration, please verify your email address by clicking the link below:\n\n"
        f"{signin_link}\n\n"
        f"This link will expire in 10 minutes for security reasons.\n\n"
        f"If you did not create this account, you can safely ignore this email."
    )
    try:
        email_service = EmailService()
        email_service.send_email( recipient = user.email, subject = subject, body = body)
        return {"message": "Verification email resent successfully"}
    except Exception as e:
        raise HTTPException(status_code=500, detail="Failed to send verification email")
@app.post("/verify-email")
async def verify_email(request: schemas.TokenRequest, db: Session = Depends(get_db)):
    try:
        email = verify_token(request.token)
        user = get_user_by_email(email, db)
        if not user:
            raise HTTPException(status_code=404, detail="User not found")
        user.is_verified = True
        db.commit()
        return {"msg": "Email verified"}
    except JWTError:
        raise HTTPException(status_code=400, detail="Invalid or expired token")

@app.post("/save-user")
async def save_user(user: schemas.UserSaveRequest, db: Session = Depends(get_db)):
    db = SessionLocal()   
    db_user = db.query(User).filter(User.email == user.email).first()
    if db_user:
        return {
            "detail": "Email already registered",
            "status": "warning"
        }
    # Create the new user
    new_user = User(email=user.email, hashed_password="social auth", ai_data=True, is_verified=True, social_id=user.id, username= user.name )
    db.add(new_user)
    db.commit()
    db.refresh(new_user)
    return {"message": "User saved successfully"}

@app.post("/api/auth/verified")
def verify_email(payload: schemas.TokenRequest, db: Session = Depends(get_db)):
    db_token = db.query(VerificationToken).filter_by(token=payload.token).first()
    if not db_token:
        raise HTTPException(status_code=400, detail="Invalid or already used verification link")

    if db_token.is_used:
        raise HTTPException(status_code=400, detail="This verification link has already been used.")

    try:
        decode_data = jwt.decode(payload.token, SECRET_KEY, algorithms=[ALGORITHM])
        email = decode_data.get("sub")
        if not email:
            return {"status": False, "message": "There is no email"}
        user = db.query(User).filter(User.email == email).first()
        if not user:
            return {"status": False, "message": "There is no email"}
        # ✅ Mark token and user verified
        user.is_verified = True
        db_token.is_used = True
        db.commit()
        return {"success": True, "message": "Email verified successfully"}
    except JWTError:
        raise HTTPException(status_code=400, detail="Invalid or expired token")


@app.post("/api/auth/verify")
def verify_token_auth(credentials: HTTPAuthorizationCredentials = Depends(security)):
    token = credentials.credentials  # Extract the Bearer token
    try:
        # Decode the token
        decoded_data = jwt.decode(token, SECRET_KEY, algorithms=[ALGORITHM])
        email = decoded_data.get("sub")
        if not email:
            return {"success": False, "message": "Token does not contain an email (sub)."}

        # You can add any additional checks here

        return {"success": True, "message": "Token is valid", "email": email}

    except JWTError:
        raise HTTPException(status_code=400, detail="Invalid or expired token")


def get_user(db: Session, user_id: int):
    return db.query(User).filter(User.id == user_id).first()
def get_user_by_email(email: str, db):
    return db.query(User).filter(User.email == email).first()

def get_users(db: Session, skip: int = 0, limit: int = 100):
    return db.query(User).offset(skip).limit(limit).all()



