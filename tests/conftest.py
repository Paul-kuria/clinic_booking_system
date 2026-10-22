import os
# Ensure environment is testing before loading app/config
os.environ["ENVIRONMENT"] = "testing"

import pytest
from datetime import time
from fastapi.testclient import TestClient
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from sqlalchemy.pool import StaticPool

from app.core.db import Base, get_db
from app.main import app
from app.models.doctor import Doctor, DoctorSchedule
from app.models.patient import Patient

# In-memory SQLite for blazing fast, isolated unit/integration tests
TEST_DATABASE_URL = "sqlite:///:memory:"

engine_test = create_engine(
    TEST_DATABASE_URL,
    connect_args={"check_same_thread": False},
    poolclass=StaticPool,
)
TestingSessionLocal = sessionmaker(
    autocommit=False, autoflush=False, bind=engine_test
)


@pytest.fixture(scope="function")
def db_session():
    """Create fresh tables for every test function, seed baseline fixtures, then drop."""
    Base.metadata.create_all(bind=engine_test)
    session = TestingSessionLocal()

    # Seed 2 test doctors
    doc1 = Doctor(
        name="Dr. Angela Test",
        email="angela.test@clinic.co.ke",
        specialty="Physiotherapy",
    )
    doc2 = Doctor(
        name="Dr. Brian Test",
        email="brian.test@clinic.co.ke",
        specialty="Rehab",
    )
    session.add_all([doc1, doc2])
    session.flush()

    # Give Dr. 1 schedules for every weekday (Mon-Sun: 0-6), 08:00 to 18:00
    for day in range(7):
        session.add(
            DoctorSchedule(
                doctor_id=doc1.id,
                day_of_week=day,
                start_time=time(8, 0),
                end_time=time(18, 0),
            )
        )

    # Give Dr. 2 schedule only for Mondays (0), 09:00 to 12:00
    session.add(
        DoctorSchedule(
            doctor_id=doc2.id,
            day_of_week=0,
            start_time=time(9, 0),
            end_time=time(12, 0),
        )
    )

    # Seed 2 test patients
    pat1 = Patient(
        name="Alice Patient",
        email="alice@test.com",
        phone="+254700000001",
    )
    pat2 = Patient(
        name="Bob Patient",
        email="bob@test.com",
        phone="+254700000002",
    )
    session.add_all([pat1, pat2])

    session.commit()

    yield session

    session.close()
    Base.metadata.drop_all(bind=engine_test)


@pytest.fixture(scope="function")
def client(db_session):
    """FastAPI TestClient using the test db session."""

    def override_get_db():
        try:
            yield db_session
        finally:
            pass

    app.dependency_overrides[get_db] = override_get_db
    with TestClient(app) as test_client:
        yield test_client
    app.dependency_overrides.clear()
