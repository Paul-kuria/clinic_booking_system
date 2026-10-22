from datetime import time
from sqlalchemy.orm import Session
from app.models.doctor import Doctor, DoctorSchedule
from app.models.patient import Patient


def seed_initial_data(db: Session) -> None:
    """
    Seeds the 5 clinic doctors, their schedules, and default patients
    if the database is fresh.
    """
    # Check if doctors are already present
    if db.query(Doctor).first() is not None:
        return

    doctors_data = [
        {
            "name": "Dr. Angela Wanjiku",
            "email": "angela.wanjiku@clinic.co.ke",
            "specialty": "Sports & Orthopedic Physiotherapy",
            # Mon to Fri (0 to 4), 08:30 - 16:30
            "schedules": [
                (day, time(8, 30), time(16, 30)) for day in range(5)
            ],
        },
        {
            "name": "Dr. Brian Otieno",
            "email": "brian.otieno@clinic.co.ke",
            "specialty": "Neuro-Rehabilitation & Spine Care",
            # Mon to Fri (0 to 4), 09:00 - 17:00
            "schedules": [(day, time(9, 0), time(17, 0)) for day in range(5)],
        },
        {
            "name": "Dr. David Kiprop",
            "email": "david.kiprop@clinic.co.ke",
            "specialty": "Musculoskeletal & Workplace Ergonomics",
            # Mon, Wed, Fri (0, 2, 4), 09:00 - 17:00
            "schedules": [(day, time(9, 0), time(17, 0)) for day in (0, 2, 4)],
        },
        {
            "name": "Dr. Esther Njeri",
            "email": "esther.njeri@clinic.co.ke",
            "specialty": "Post-Surgical Rehab & Pain Management",
            # Mon to Fri (0 to 4), 10:00 - 18:00
            "schedules": [(day, time(10, 0), time(18, 0)) for day in range(5)],
        },
    ]

    for d in doctors_data:
        doctor = Doctor(name=d["name"], email=d["email"], specialty=d["specialty"])
        db.add(doctor)
        db.flush()

        for day, start_t, end_t in d["schedules"]:
            sched = DoctorSchedule(
                doctor_id=doctor.id,
                day_of_week=day,
                start_time=start_t,
                end_time=end_t,
            )
            db.add(sched)

    # Seed 2 sample patients if none exist
    if db.query(Patient).first() is None:
        patient1 = Patient(
            name="John Doe",
            email="john.doe@example.com",
            phone="+254712345678",
        )
        patient2 = Patient(
            name="Jane Smith",
            email="jane.smith@example.com",
            phone="+254798765432",
        )
        db.add_all([patient1, patient2])

    db.commit()
