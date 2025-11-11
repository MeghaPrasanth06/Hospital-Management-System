# models.py
from sqlalchemy import Column, Integer, String, Boolean, DateTime, ForeignKey, Enum, Text
from sqlalchemy.orm import relationship
from sqlalchemy.sql import func
from database import Base
import enum

class RoleEnum(str, enum.Enum):
    patient = "patient"
    doctor = "doctor"
    admin = "admin"

class User(Base):
    __tablename__ = "users"
    id = Column(Integer, primary_key=True, index=True)
    full_name = Column(String, nullable=False)
    email = Column(String, unique=True, index=True, nullable=True)
    contact = Column(String, unique=True, index=True, nullable=True)
    hashed_password = Column(String, nullable=False)
    role = Column(Enum(RoleEnum), default=RoleEnum.patient)
    is_active = Column(Boolean, default=True)
    is_approved = Column(Boolean, default=False)  # doctors need admin approval
    created_at = Column(DateTime(timezone=True), server_default=func.now())

class DoctorProfile(Base):
    __tablename__ = "doctor_profiles"
    id = Column(Integer, primary_key=True)
    user_id = Column(Integer, ForeignKey("users.id"), unique=True)
    speciality = Column(String, nullable=True)
    timings = Column(String, nullable=True)  # simple CSV or text
    location = Column(String, nullable=True)

class AppointmentStatus(str, enum.Enum):
    booked = "booked"
    cancelled = "cancelled"
    completed = "completed"

class Appointment(Base):
    __tablename__ = "appointments"
    id = Column(Integer, primary_key=True, index=True)
    patient_id = Column(Integer, ForeignKey("users.id"))
    doctor_id = Column(Integer, ForeignKey("users.id"))
    scheduled_time = Column(DateTime, nullable=False)
    status = Column(Enum(AppointmentStatus), default=AppointmentStatus.booked)
    prescription_qr = Column(Text, nullable=True)
    created_at = Column(DateTime(timezone=True), server_default=func.now())

class SmartQueueEntry(Base):
    __tablename__ = "smart_queue"
    id = Column(Integer, primary_key=True)
    appointment_id = Column(Integer, ForeignKey("appointments.id"), unique=True)
    doctor_id = Column(Integer, ForeignKey("users.id"))
    queue_position = Column(Integer)
    created_at = Column(DateTime(timezone=True), server_default=func.now())

class BedStatus(str, enum.Enum):
    available = "available"
    occupied = "occupied"
    cleaning = "cleaning"

class Bed(Base):
    __tablename__ = "beds"
    id = Column(Integer, primary_key=True)
    ward = Column(String, nullable=True)
    number = Column(String, nullable=True)
    status = Column(Enum(BedStatus), default=BedStatus.available)

class Medicine(Base):
    __tablename__ = "medicines"
    id = Column(Integer, primary_key=True)
    name = Column(String, nullable=False)
    quantity = Column(Integer, default=0)
    threshold = Column(Integer, default=1)
