from datetime import datetime, timezone
from pydantic import BaseModel, ConfigDict, Field, field_validator
from app.models.appointment import AppointmentStatus


class AppointmentCreate(BaseModel):
    doctor_id: int
    patient_id: int
    start_time: datetime

    @field_validator("start_time")
    @classmethod
    def validate_slot_alignment(cls, v: datetime) -> datetime:
        # Normalize naive datetime to UTC if no timezone is provided
        if v.tzinfo is None:
            v = v.replace(tzinfo=timezone.utc)
        else:
            v = v.astimezone(timezone.utc)

        # Must fall on 30-minute boundaries (:00 or :30) with 0 seconds
        if v.minute not in (0, 30) or v.second != 0 or v.microsecond != 0:
            raise ValueError(
                "Appointment start_time must be aligned to a 30-minute boundary (e.g., :00 or :30)."
            )
        return v


class AppointmentCancel(BaseModel):
    reason: str = Field(
        ...,
        min_length=3,
        max_length=500,
        description="Reason for cancellation",
    )


class AppointmentReschedule(BaseModel):
    new_start_time: datetime

    @field_validator("new_start_time")
    @classmethod
    def validate_new_slot_alignment(cls, v: datetime) -> datetime:
        if v.tzinfo is None:
            v = v.replace(tzinfo=timezone.utc)
        else:
            v = v.astimezone(timezone.utc)

        if v.minute not in (0, 30) or v.second != 0 or v.microsecond != 0:
            raise ValueError(
                "New start_time must be aligned to a 30-minute boundary (e.g., :00 or :30)."
            )
        return v


class AppointmentOut(BaseModel):
    id: int
    doctor_id: int
    patient_id: int
    start_time: datetime
    end_time: datetime
    status: AppointmentStatus
    cancellation_reason: str | None = None
    created_at: datetime
    updated_at: datetime

    model_config = ConfigDict(from_attributes=True)
