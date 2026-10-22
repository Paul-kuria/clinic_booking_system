from datetime import datetime
from pydantic import BaseModel, ConfigDict
from app.models.appointment import AppointmentStatus


class PatientOut(BaseModel):
    id: int
    name: str
    email: str
    phone: str
    created_at: datetime

    model_config = ConfigDict(from_attributes=True)


class PatientAppointmentOut(BaseModel):
    id: int
    doctor_id: int
    doctor_name: str
    doctor_specialty: str
    start_time: datetime
    end_time: datetime
    status: AppointmentStatus
    cancellation_reason: str | None = None

    model_config = ConfigDict(from_attributes=True)
