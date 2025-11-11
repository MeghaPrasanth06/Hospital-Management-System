# main.py
import os
from fastapi import FastAPI, Depends, HTTPException, status, Body
from fastapi.middleware.cors import CORSMiddleware
from sqlalchemy.orm import Session
from database import SessionLocal, engine
import models, schemas, crud, auth
from auth import create_access_token, decode_token, verify_password
from dotenv import load_dotenv
from fastapi.security import OAuth2PasswordBearer

load_dotenv()
models.Base.metadata.create_all(bind=engine)

app = FastAPI(title="Smart Hospital Management System")

origins = ["http://localhost:3000", "http://127.0.0.1:3000"]
app.add_middleware(CORSMiddleware, allow_origins=origins, allow_credentials=True, allow_methods=["*"], allow_headers=["*"])

def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()

# register
@app.post("/register/", response_model=schemas.UserOut)
def register(user_in: schemas.UserCreate, db: Session = Depends(get_db)):
    if user_in.email:
        if crud.get_user_by_email(db, user_in.email):
            raise HTTPException(400, "Email already registered")
    if user_in.contact:
        if crud.get_user_by_contact(db, user_in.contact):
            raise HTTPException(400, "Contact already registered")
    user = crud.create_user(db, user_in)
    # auto-approve patients
    if user.role == models.RoleEnum.patient:
        user.is_approved = True
        db.commit()
    return user

# login
from pydantic import BaseModel
class LoginData(BaseModel):
    username: str
    password: str

@app.post("/login/", response_model=schemas.Token)
def login(data: LoginData, db: Session = Depends(get_db)):
    # username may be email or contact
    user = None
    if "@" in data.username:
        user = crud.get_user_by_email(db, data.username)
    else:
        user = crud.get_user_by_contact(db, data.username)
    if not user or not auth.verify_password(data.password, user.hashed_password):
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Incorrect credentials")
    if user.role == models.RoleEnum.doctor and not user.is_approved:
        raise HTTPException(status_code=403, detail="Doctor not yet approved")
    token = create_access_token({"user_id": user.id, "role": user.role.value})
    return {"access_token": token, "token_type": "bearer"}

# oauth2 helper
oauth2_scheme = OAuth2PasswordBearer(tokenUrl="login/")

def get_current_user(token: str = Depends(oauth2_scheme), db: Session = Depends(get_db)):
    payload = decode_token(token)
    if not payload:
        raise HTTPException(status_code=401, detail="Invalid token")
    user = crud.get_user(db, int(payload.get("user_id")))
    if not user:
        raise HTTPException(status_code=401, detail="User not found")
    return user

# doctors list
@app.get("/doctors/", response_model=list[schemas.UserOut])
def doctors(db: Session = Depends(get_db)):
    return crud.list_doctors(db)

# create / get appointments
@app.post("/appointments/", response_model=schemas.AppointmentOut)
def book_appointment(appt: schemas.AppointmentIn, db: Session = Depends(get_db)):
    # validate existence
    p = crud.get_user(db, appt.patient_id)
    d = crud.get_user(db, appt.doctor_id)
    if not p or not d:
        raise HTTPException(404, "Patient or Doctor not found")
    res = crud.create_appointment(db, appt)
    return res

@app.post("/appointments/{appointment_id}/cancel")
def cancel(appointment_id: int, db: Session = Depends(get_db), current_user = Depends(get_current_user)):
    appt = crud.cancel_appointment(db, appointment_id)
    if not appt:
        raise HTTPException(404, "Appointment not found")
    return {"ok": True}

@app.post("/appointments/{appointment_id}/complete")
def complete(appointment_id: int, prescription_text: str = Body(None), db: Session = Depends(get_db), current_user = Depends(get_current_user)):
    appt = crud.complete_appointment(db, appointment_id, prescription_text)
    if not appt:
        raise HTTPException(404, "Appointment not found")
    return {"ok": True, "prescription_qr": appt.prescription_qr}

@app.get("/queue/{doctor_id}")
def get_queue(doctor_id: int, db: Session = Depends(get_db)):
    return crud.get_queue_for_doctor(db, doctor_id)

@app.get("/beds/", response_model=list[schemas.BedOut])
def get_beds(db: Session = Depends(get_db)):
    return crud.get_beds(db)

@app.post("/beds/{bed_id}/update")
def update_bed(bed_id: int, status: str = Body(...), db: Session = Depends(get_db), current_user = Depends(get_current_user)):
    # only doctor/admin
    if current_user.role not in (models.RoleEnum.doctor, models.RoleEnum.admin):
        raise HTTPException(403, "Not permitted")
    bed = crud.update_bed_status(db, bed_id, status)
    if not bed:
        raise HTTPException(404, "Bed not found")
    return bed

@app.get("/medicines/", response_model=list[schemas.MedicineOut])
def medicines(db: Session = Depends(get_db)):
    return crud.list_medicines(db)

@app.post("/medicines/{med_id}/purchase")
def purchase_med(med_id: int, patient_id: int = Body(...), qty: int = Body(1), db: Session = Depends(get_db)):
    try:
        order = crud.purchase_medicine(db, patient_id, med_id, qty)
        return {"ok": True}
    except Exception as e:
        raise HTTPException(400, str(e))

@app.post("/admin/approve_doctor/{user_id}")
def approve_doctor(user_id: int, db: Session = Depends(get_db), current_user = Depends(get_current_user)):
    if current_user.role != models.RoleEnum.admin:
        raise HTTPException(403, "Not permitted")
    user = crud.get_user(db, user_id)
    if not user or user.role != models.RoleEnum.doctor:
        raise HTTPException(404, "Doctor not found")
    user.is_approved = True
    db.commit()
    return {"ok": True}

@app.get("/")
def root():
    return {"message": "Smart Hospital Backend Running"}
