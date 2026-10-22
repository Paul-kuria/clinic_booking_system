from datetime import date
from fastapi import APIRouter, Depends, Query, status
from sqlalchemy.orm import Session
from app.core.db import get_db
from app.models.doctor import Doctor
from app.schemas.doctor import DoctorOut, DoctorAvailabilityResponse
from app.services.doctor_service import (
    get_doctor_availability,
    get_doctor_by_id,
)

router = APIRouter(prefix="/doctors", tags=["Doctors"])


@router.get(
    "",
    response_model=list[DoctorOut],
    summary="List all clinic doctors and their working schedules",
)
def list_doctors(db: Session = Depends(get_db)):
    return db.query(Doctor).all()


@router.get(
    "/{id}/availability",
    response_model=DoctorAvailabilityResponse,
    summary="Get available 30-minute slots for a doctor on a given date",
)
def get_availability(
    id: int,
    date: date = Query(
        ...,
        description="Target date in YYYY-MM-DD format (evaluated in Africa/Nairobi timezone)",
        examples=["2026-10-25"],
    ),
    db: Session = Depends(get_db),
):
    return get_doctor_availability(db=db, doctor_id=id, target_date=date)
