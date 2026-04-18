# =============================================================================
# config.py — Flask backend configuration.
# All secrets are loaded from environment variables (never hardcoded).
# =============================================================================

import os
from dotenv import load_dotenv

load_dotenv()


class BaseConfig:
    # Flask
    SECRET_KEY = os.getenv("SECRET_KEY", "change-this-in-production")
    DEBUG      = False
    TESTING    = False

    # PostgreSQL
    SQLALCHEMY_DATABASE_URI = os.getenv(
        "DATABASE_URL",
        "postgresql://lyion:lyion_pass@localhost:5432/lyion_db",
    )
    SQLALCHEMY_TRACK_MODIFICATIONS = False
    SQLALCHEMY_ENGINE_OPTIONS = {
        "pool_pre_ping": True,
        "pool_size":     10,
        "max_overflow":  20,
    }

    # JWT
    JWT_SECRET_KEY      = os.getenv("JWT_SECRET_KEY", "jwt-secret-change-me")
    JWT_ACCESS_TOKEN_EXPIRES  = 3600        # 1 hour (seconds)
    JWT_REFRESH_TOKEN_EXPIRES = 30 * 86400  # 30 days

    # Station authentication
    STATION_API_KEY = os.getenv("STATION_API_KEY", "station-api-key-change-me")

    # Rental settings (institution-configurable via env vars)
    DEPOSIT_AMOUNT        = float(os.getenv("DEPOSIT_AMOUNT",  "5.00"))  # EUR
    MAX_RENTAL_HOURS      = int(os.getenv("MAX_RENTAL_HOURS",  "24"))
    SCHOOL_NAME           = os.getenv("SCHOOL_NAME",           "Université Ly-ion")
    SCHOOL_LOGO_URL       = os.getenv("SCHOOL_LOGO_URL",       "")
    BATTERY_CHARGE_THRESHOLD = int(os.getenv("BATTERY_CHARGE_THRESHOLD", "80"))


class DevelopmentConfig(BaseConfig):
    DEBUG = True


class ProductionConfig(BaseConfig):
    pass


class TestingConfig(BaseConfig):
    TESTING = True
    SQLALCHEMY_DATABASE_URI = "sqlite:///:memory:"


_configs = {
    "development": DevelopmentConfig,
    "production":  ProductionConfig,
    "testing":     TestingConfig,
}


def get_config():
    env = os.getenv("FLASK_ENV", "development")
    return _configs.get(env, DevelopmentConfig)
