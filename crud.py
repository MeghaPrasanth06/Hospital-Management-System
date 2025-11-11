# crud.py
from sqlalchemy.orm import Session
from sqlalchemy import func
import models, schemas
from auth import get_password_hash
from utils import send_email_stub, make_qr_base64
from datetime import datetime

# Users
def create_user(db: Session, user_in: schemas.UserCreate):
    hashed = get_password_hash(user_in.password)
    db_user = models.User(
        full_name=user_in.full_name,
        email=user_in.email,
        contact=user_in.contact,
        hashed_password=hashed,
        role=user_in.role.value if hasattr(user_in.role, "value") else user_in.role
    )
    db.add(db_user)
    db.commit()
    db.refresh(db_user)
    return db_user

def get_user_by_email(db: Session, email: str):
    return db.query(models.User).filter(func.lower(models.User.email) == email.lower()).first()

def get_user_by_contact(db: Session, contact: str):
    return db.query(models.User).filter(models.User.contact == contact).first()

def get_user(db: Session, user_id: int):
    return db.get(models.User, user_id)

def list_doctors(db: Session):
    return db.query(models.User).filter(models.User.role == models.RoleEnum.doctor, models.User.is_approved == True).all()

# Doctor profile
def create_or_update_doctor_profile(db: Session, user_id: int, profile: schemas.DoctorProfileIn):
    existing = db.query(models.DoctorProfile).filter(models.DoctorProfile.user_id == user_id).first()
    if existing:
        existing.speciality = profile.speciality
        existing.timings = profile.timings
        existing.location = profile.location
        db.commit()
        db.refresh(existing)
        return existing
    dp = models.DoctorProfile(user_id=user_id, speciality=profile.speciality, timings=profile.timings, location=profile.location)
    db.add(dp)
    db.commit()
    db.refresh(dp)
    return dp

# Appointments + queue
def create_appointment(db: Session, appt_in: schemas.AppointmentIn):
    appt = models.Appointment(patient_id=appt_in.patient_id, doctor_id=appt_in.doctor_id, scheduled_time=appt_in.scheduled_time)
    db.add(appt)
    db.commit()
    db.refresh(appt)
    # add to queue
    max_pos = db.query(func.max(models.SmartQueueEntry.queue_position)).filter(models.SmartQueueEntry.doctor_id == appt_in.doctor_id).scalar() or 0
    entry = models.SmartQueueEntry(appointment_id=appt.id, doctor_id=appt_in.doctor_id, queue_position=max_pos + 1)
    db.add(entry)
    db.commit()
    db.refresh(entry)
    # notify
    patient = get_user(db, appt_in.patient_id)
    if patient and patient.email:
        send_email_stub(patient.email, "Appointment Confirmed", f"Queue number: {entry.queue_position}")
    return appt

def cancel_appointment(db: Session, appointment_id: int):
    appt = db.get(models.Appointment, appointment_id)
    if not appt:
        return None
    appt.status = models.AppointmentStatus.cancelled
    db.commit()
    # remove queue entry and update positions
    entry = db.query(models.SmartQueueEntry).filter(models.SmartQueueEntry.appointment_id == appointment_id).first()
    if entry:
        doctor = entry.doctor_id
        pos = entry.queue_position
        db.delete(entry)
        db.commit()
        db.query(models.SmartQueueEntry).filter(models.SmartQueueEntry.doctor_id == doctor, models.SmartQueueEntry.queue_position > pos).update({models.SmartQueueEntry.queue_position: models.SmartQueueEntry.queue_position - 1}, synchronize_session=False)
        db.commit()
    patient = get_user(db, appt.patient_id)
    if patient and patient.email:
        send_email_stub(patient.email, "Appointment Cancelled", "Your appointment was cancelled.")
    return appt

def complete_appointment(db: Session, appointment_id: int, prescription_text: str | None = None):
    appt = db.get(models.Appointment, appointment_id)
    if not appt:
        return None
    appt.status = models.AppointmentStatus.completed
    if prescription_text:
        qr = make_qr_base64(prescription_text)
        appt.prescription_qr = qr
    db.commit()
    # remove from queue and shift
    entry = db.query(models.SmartQueueEntry).filter(models.SmartQueueEntry.appointment_id == appointment_id).first()
    if entry:
        doc = entry.doctor_id
        ppos = entry.queue_position
        db.delete(entry)
        db.commit()
        db.query(models.SmartQueueEntry).filter(models.SmartQueueEntry.doctor_id == doc, models.SmartQueueEntry.queue_position > ppos).update({models.SmartQueueEntry.queue_position: models.SmartQueueEntry.queue_position - 1}, synchronize_session=False)
        db.commit()
    patient = get_user(db, appt.patient_id)
    if patient and patient.email and appt.prescription_qr:
        send_email_stub(patient.email, "Prescription Ready", "Your prescription QR is available.")
    return appt

def get_queue_for_doctor(db: Session, doctor_id: int):
    return db.query(models.SmartQueueEntry).filter(models.SmartQueueEntry.doctor_id == doctor_id).order_by(models.SmartQueueEntry.queue_position).all()

# Beds & Medicines
def get_beds(db: Session):
    return db.query(models.Bed).all()

def update_bed_status(db: Session, bed_id: int, status):
    bed = db.get(models.Bed, bed_id)
    if not bed:
        return None
    bed.status = status
    db.commit()
    db.refresh(bed)
    return bed

def list_medicines(db: Session):
    return db.query(models.Medicine).all()

def purchase_medicine(db: Session, patient_id: int, medicine_id: int, qty: int = 1):
    med = db.get(models.Medicine, medicine_id)
    if not med:
        raise ValueError("Medicine not found")
    if med.quantity < qty:
        raise ValueError("Out of stock")
    med.quantity -= qty
    db.commit()
    return med
