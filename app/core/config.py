from zoneinfo import ZoneInfo
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    PROJECT_NAME: str = "Clinic Booking System"
    ENVIRONMENT: str = "development"
    DATABASE_URL: str = "postgresql://clinic_user:clinic_password@localhost:5432/clinic_db"
    CLINIC_TIMEZONE: str = "Africa/Nairobi"

    # Business logic constraints
    SLOT_DURATION_MINUTES: int = 30
    MIN_ADVANCE_BOOKING_HOURS: int = 1

    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        extra="ignore"
    )

    @property
    def sync_database_url(self) -> str:
        """
        Ensures SQLAlchemy uses psycopg2 driver even if URI is postgres:// or postgresql://
        """
        url = self.DATABASE_URL
        if url.startswith("postgres://"):
            url = url.replace("postgres://", "postgresql+psycopg2://", 1)
        elif url.startswith("postgresql://") and not url.startswith("postgresql+"):
            url = url.replace("postgresql://", "postgresql+psycopg2://", 1)
        return url

    @property
    def timezone_info(self) -> ZoneInfo:
        return ZoneInfo(self.CLINIC_TIMEZONE)


settings = Settings()
