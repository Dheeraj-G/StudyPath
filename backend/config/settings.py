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
    
    # Google Cloud settings
    GOOGLE_CLOUD_PROJECT: str = os.getenv("GOOGLE_CLOUD_PROJECT", "")
    GCS_BUCKET_NAME: str = os.getenv("GCS_BUCKET_NAME", "studypath-uploads")
    
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
