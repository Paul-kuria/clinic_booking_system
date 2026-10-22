import enum
from datetime import datetime, timezone
from sqlalchemy import (
    Column,
    Integer,
    ForeignKey,
    DateTime,
    Text,
    Enum,
    Index,
    text,
)
from sqlalchemy.orm import relationship
from app.core.db import Base


class AppointmentStatus(str, enum.Enum):
    BOOKED = "BOOKED"
    CANCELLED = "CANCELLED"


class Appointment(Base):
    __tablename__ = "appointments"

    id = Column(Integer, primary_key=True, index=True)
    doctor_id = Column(
        Integer,
        ForeignKey("doctors.id", ondelete="RESTRICT"),
        nullable=False,
        index=True,
    )
    patient_id = Column(
        Integer,
        ForeignKey("patients.id", ondelete="RESTRICT"),
        nullable=False,
        index=True,
    )
    start_time = Column(DateTime(timezone=True), nullable=False, index=True)
    end_time = Column(DateTime(timezone=True), nullable=False)
    status = Column(
        Enum(
            AppointmentStatus,
            name="appointment_status",
            values_callable=lambda obj: [e.value for e in obj],
        ),
        nullable=False,
        default=AppointmentStatus.BOOKED,
        index=True,
    )
    cancellation_reason = Column(Text, nullable=True)
    created_at = Column(
        DateTime(timezone=True),
        default=lambda: datetime.now(timezone.utc),
        nullable=False,
    )
    updated_at = Column(
        DateTime(timezone=True),
        default=lambda: datetime.now(timezone.utc),
        onupdate=lambda: datetime.now(timezone.utc),
        nullable=False,
    )

    doctor = relationship("Doctor", back_populates="appointments")
    patient = relationship("Patient", back_populates="appointments")

    __table_args__ = (
        # Partial unique index: Doctor cannot have two active (BOOKED) appointments at the same start time
        Index(
            "uq_doctor_active_slot",
            "doctor_id",
            "start_time",
            unique=True,
            postgresql_where=text("status = 'BOOKED'"),
        ),
        # Partial unique index: Patient cannot have two active (BOOKED) appointments at the same start time
        Index(
            "uq_patient_active_slot",
            "patient_id",
            "start_time",
            unique=True,
            postgresql_where=text("status = 'BOOKED'"),
        ),
    )
