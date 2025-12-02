import os
from pathlib import Path
from pydantic import EmailStr, SecretStr

try:
    from dotenv import load_dotenv

    _env_path = Path(".") / ".env"
    if _env_path.exists():
        load_dotenv(dotenv_path=_env_path)
except Exception:
    pass


class Config:

    DB_URL = os.getenv("DB_URL")
    REDIS_URL = os.getenv("REDIS_URL", "redis://localhost:6379/0")
    # Use `or` to guard against empty-string environment values (e.g. on some platforms)
    CACHE_TTL = int(os.getenv("CACHE_TTL") or 86400)
    JWT_SECRET = os.getenv("JWT_SECRET", "your_jwt_secret_key")
    JWT_ALGORITHM = os.getenv("JWT_ALGORITHM", "HS256")
    JWT_EXPIRATION_SECONDS = int(os.getenv("JWT_EXPIRATION_SECONDS") or 3600)
    JWT_REFRESH_EXPIRATION_SECONDS = int(
        os.getenv("JWT_REFRESH_EXPIRATION_SECONDS") or 604800
    )

    MAIL_USERNAME: EmailStr = "yurii.osadchiy@meta.ua"
    MAIL_PASSWORD: SecretStr = SecretStr("Mqwertyui86!")
    MAIL_FROM: EmailStr = "yurii.osadchiy@meta.ua"
    MAIL_PORT: int = 465
    MAIL_SERVER: str = "smtp.meta.ua"
    MAIL_FROM_NAME: str = "Rest API Service"
    MAIL_STARTTLS: bool = False
    MAIL_SSL_TLS: bool = True
    USE_CREDENTIALS: bool = True
    VALIDATE_CERTS: bool = True

    ORIGINS = os.getenv("ORIGINS", "http://localhost:3000").split(",")

    CLOUDINARY_NAME = "dprywbm8e"
    CLOUDINARY_API_KEY = 459371715835687
    CLOUDINARY_API_SECRET = "jF_YVIfSr6hjlHbM37WJ9x54tEs"


config = Config
