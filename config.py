from pydantic_settings import BaseSettings
from functools import lru_cache
from typing import Optional

class Settings(BaseSettings):
    whatsapp_access_token: str
    whatsapp_phone_number_id: str
    whatsapp_verify_token: str = "memora_verify_token"
    anthropic_api_key: str
    google_credentials_path: str = "credentials.json"
    google_drive_root_folder: str = "AI-Storage"
    redis_url: str = "redis://redis:6379"
    redis_password: Optional[str] = "memora_redis_pass"
    secret_key: str = "change-me-in-production"
    admin_secret: str = "admin_secret_change_me"
    debug: bool = True
    sqlite_db_path: str = "./memora.db"
    chroma_db_path: str = "./chroma_db"
    temp_dir: str = "./temp_files"
    
    class Config:
        env_file = ".env"
        case_sensitive = False

@lru_cache()
def get_settings() -> Settings:
    return Settings()
