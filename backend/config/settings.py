"""
Configuration settings for StudyPath backend
"""

from pydantic_settings import BaseSettings
from typing import Optional
import os

class Settings(BaseSettings):
    # Server settings
    PORT: int = 8000
    DEBUG: bool = True
    HOST: str = "0.0.0.0"
    
    # Firebase settings
    FIREBASE_PROJECT_ID: str = os.getenv("FIREBASE_PROJECT_ID", "")
    FIREBASE_PRIVATE_KEY: str = os.getenv("FIREBASE_PRIVATE_KEY", "")
    FIREBASE_CLIENT_EMAIL: str = os.getenv("FIREBASE_CLIENT_EMAIL", "")
    
    # Google Cloud settings (Firebase Storage uses GCS bucket)
    GOOGLE_CLOUD_PROJECT: str = os.getenv("GOOGLE_CLOUD_PROJECT", "studypath-29e9b")
    GCS_BUCKET_NAME: str = os.getenv("GCS_BUCKET_NAME", "studypath-29e9b.firebasestorage.app")
    GOOGLE_APPLICATION_CREDENTIALS: str = os.getenv("GOOGLE_APPLICATION_CREDENTIALS", "service-account.json")
    # Uploads path configuration
    UPLOADS_DIR_NAME: str = os.getenv("UPLOADS_DIR_NAME", "uploads")
    
    # Redis settings
    REDIS_URL: str = os.getenv("REDIS_URL", "redis://localhost:6379")
    
    # LangGraph settings
    LANGGRAPH_API_URL: str = os.getenv("LANGGRAPH_API_URL", "http://localhost:8001")
    
    # Pub/Sub settings
    PUBSUB_TOPIC_NAME: str = os.getenv("PUBSUB_TOPIC_NAME", "studypath-processing")
    
    class Config:
        env_file = ".env"

def get_settings() -> Settings:
    return Settings()
