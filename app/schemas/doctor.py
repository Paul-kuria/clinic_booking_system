from datetime import date, time, datetime
from pydantic import BaseModel, ConfigDict


class DoctorScheduleOut(BaseModel):
    id: int
    day_of_week: int
    start_time: time
    end_time: time

    model_config = ConfigDict(from_attributes=True)


class DoctorOut(BaseModel):
    id: int
    name: str
    email: str
    specialty: str
    schedules: list[DoctorScheduleOut] = []

    model_config = ConfigDict(from_attributes=True)


class TimeSlotOut(BaseModel):
    start_time: datetime
    end_time: datetime


class DoctorAvailabilityResponse(BaseModel):
    doctor_id: int
    doctor_name: str
    date: date
    available_slots: list[TimeSlotOut]
