from fastapi import APIRouter, Depends, status
from sqlalchemy.orm import Session
from app.core.db import get_db
from app.schemas.appointment import (
    AppointmentCreate,
    AppointmentCancel,
    AppointmentReschedule,
    AppointmentOut,
)
from app.services.appointment_service import (
    book_appointment,
    cancel_appointment,
    reschedule_appointment,
)

router = APIRouter(prefix="/appointments", tags=["Appointments"])


@router.post(
    "",
    response_model=AppointmentOut,
    status_code=status.HTTP_201_CREATED,
    summary="Book a doctor's 30-minute slot",
)
def create_appointment(
    payload: AppointmentCreate, db: Session = Depends(get_db)
):
    return book_appointment(db=db, payload=payload)


@router.patch(
    "/{id}/cancel",
    response_model=AppointmentOut,
    summary="Cancel an appointment with a reason",
)
def cancel(
    id: int, payload: AppointmentCancel, db: Session = Depends(get_db)
):
    return cancel_appointment(db=db, appointment_id=id, payload=payload)


@router.patch(
    "/{id}/reschedule",
    response_model=AppointmentOut,
    summary="Reschedule an appointment to a new slot",
)
def reschedule(
    id: int, payload: AppointmentReschedule, db: Session = Depends(get_db)
):
    return reschedule_appointment(db=db, appointment_id=id, payload=payload)
