import os
from pydantic_settings import BaseSettings

class Settings(BaseSettings):
    DATABASE_URL: str = f"sqlite:///{os.path.abspath(os.path.join(os.path.dirname(__file__), 'data', 'rh_project.db'))}"
    JWT_SECRET: str = "secret_token_uuid"
    UPLOAD_DIR: str = "uploads/photos"

    class Config:
        env_file = ".env"
        env_file_encoding = "utf-8"

settings = Settings()