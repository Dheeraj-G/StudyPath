"""
Data Models for StudyPath Application
Pydantic models for study plans, learning progress, and user data
"""

from pydantic import BaseModel, Field
from typing import Dict, List, Optional, Any, Union
from datetime import datetime
from enum import Enum

class FileStatus(str, Enum):
    UPLOADED = "uploaded"
    PROCESSING = "processing"
    PROCESSED = "processed"
    FAILED = "failed"

class ProcessingStatus(str, Enum):
    PENDING = "pending"
    IN_PROGRESS = "in_progress"
    COMPLETED = "completed"
    FAILED = "failed"

class StudyPlanStatus(str, Enum):
    ACTIVE = "active"
    COMPLETED = "completed"
    ARCHIVED = "archived"

class LearningLevel(str, Enum):
    BEGINNER = "beginner"
    INTERMEDIATE = "intermediate"
    ADVANCED = "advanced"

# File Upload Models
class FileUploadRequest(BaseModel):
    file_name: str = Field(..., description="Name of the file to upload")
    file_type: str = Field(..., description="Type/category of the file")
    file_size: int = Field(..., description="Size of the file in bytes")
    content_type: str = Field(..., description="MIME type of the file")

class FileUploadResponse(BaseModel):
    upload_url: str = Field(..., description="Signed URL for uploading")
    file_id: str = Field(..., description="Unique identifier for the file")
    file_path: str = Field(..., description="Path where file will be stored")
    expires_at: str = Field(..., description="Expiration time of the upload URL")
    fields: Dict[str, str] = Field(..., description="Additional form fields")

class FileUploadComplete(BaseModel):
    file_id: str = Field(..., description="File identifier")
    file_path: str = Field(..., description="Path of the uploaded file")
    file_size: int = Field(..., description="Actual size of uploaded file")

class FileMetadata(BaseModel):
    file_id: str
    user_id: str
    file_path: str
    file_name: str
    file_size: int
    content_type: str
    uploaded_at: datetime
    status: FileStatus
    gcs_metadata: Optional[Dict[str, Any]] = None
    processing_results: Optional[Dict[str, Any]] = None
    created_at: Optional[datetime] = None
    updated_at: Optional[datetime] = None

# Study Plan Models
class StudyTopic(BaseModel):
    topic_id: str = Field(..., description="Unique identifier for the topic")
    title: str = Field(..., description="Title of the study topic")
    description: str = Field(..., description="Description of what will be learned")
    estimated_duration: int = Field(..., description="Estimated time in minutes")
    difficulty_level: LearningLevel = Field(..., description="Difficulty level")
    prerequisites: List[str] = Field(default=[], description="Required topics to complete first")
    resources: List[Dict[str, str]] = Field(default=[], description="Learning resources")
    completed: bool = Field(default=False, description="Whether topic is completed")
    completed_at: Optional[datetime] = None

class StudyPlan(BaseModel):
    plan_id: Optional[str] = None
    user_id: str
    title: str = Field(..., description="Title of the study plan")
    description: str = Field(..., description="Description of the study plan")
    topics: List[StudyTopic] = Field(..., description="List of study topics")
    total_estimated_duration: int = Field(..., description="Total estimated time in minutes")
    created_at: Optional[datetime] = None
    updated_at: Optional[datetime] = None
    status: StudyPlanStatus = Field(default=StudyPlanStatus.ACTIVE)
    progress_percentage: float = Field(default=0.0, description="Completion percentage")

class StudyPlanRequest(BaseModel):
    title: str = Field(..., description="Title for the study plan")
    description: str = Field(..., description="Description of learning goals")
    file_ids: List[str] = Field(..., description="Files to analyze for study plan")
    learning_goals: List[str] = Field(default=[], description="Specific learning objectives")
    time_constraints: Optional[int] = Field(None, description="Available time in minutes")

# Learning Progress Models
class LearningSession(BaseModel):
    session_id: Optional[str] = None
    user_id: str
    study_plan_id: Optional[str] = None
    topic_id: Optional[str] = None
    session_type: str = Field(..., description="Type of learning session")
    duration_minutes: int = Field(..., description="Duration of the session")
    questions_answered: int = Field(default=0, description="Number of questions answered")
    correct_answers: int = Field(default=0, description="Number of correct answers")
    topics_covered: List[str] = Field(default=[], description="Topics covered in session")
    notes: Optional[str] = Field(None, description="User notes from the session")
    created_at: Optional[datetime] = None

class LearningProgress(BaseModel):
    user_id: str
    total_study_time: int = Field(default=0, description="Total study time in minutes")
    sessions_completed: int = Field(default=0, description="Number of completed sessions")
    topics_completed: int = Field(default=0, description="Number of completed topics")
    current_streak: int = Field(default=0, description="Current daily streak")
    longest_streak: int = Field(default=0, description="Longest daily streak")
    accuracy_percentage: float = Field(default=0.0, description="Overall accuracy percentage")
    last_activity: Optional[datetime] = None
    updated_at: Optional[datetime] = None

# Chat and Communication Models
class ChatMessage(BaseModel):
    message_id: Optional[str] = None
    user_id: str
    role: str = Field(..., description="Role: 'user' or 'assistant'")
    content: str = Field(..., description="Message content")
    context: Optional[Dict[str, Any]] = Field(None, description="Additional context")
    file_references: List[str] = Field(default=[], description="Referenced file IDs")
    created_at: Optional[datetime] = None

class ChatRequest(BaseModel):
    message: str = Field(..., description="User message")
    context: Optional[Dict[str, Any]] = Field(None, description="Additional context")
    file_ids: Optional[List[str]] = Field(None, description="Relevant file IDs")

# Processing Task Models
class ProcessingTask(BaseModel):
    task_id: Optional[str] = None
    user_id: str
    task_type: str = Field(..., description="Type of processing task")
    file_ids: List[str] = Field(..., description="Files being processed")
    status: ProcessingStatus = Field(default=ProcessingStatus.PENDING)
    progress_percentage: float = Field(default=0.0)
    result_data: Optional[Dict[str, Any]] = Field(None, description="Processing results")
    error_message: Optional[str] = Field(None, description="Error message if failed")
    created_at: Optional[datetime] = None
    updated_at: Optional[datetime] = None
    completed_at: Optional[datetime] = None

class ProcessingRequest(BaseModel):
    file_ids: List[str] = Field(..., description="Files to process")
    processing_type: str = Field(default="study_plan", description="Type of processing")
    options: Optional[Dict[str, Any]] = Field(None, description="Processing options")

# User Profile Models
class UserProfile(BaseModel):
    user_id: str
    email: str
    display_name: Optional[str] = None
    photo_url: Optional[str] = None
    learning_preferences: Dict[str, Any] = Field(default={}, description="User learning preferences")
    study_goals: List[str] = Field(default=[], description="User's study goals")
    preferred_language: str = Field(default="en", description="Preferred language")
    timezone: str = Field(default="UTC", description="User's timezone")
    created_at: Optional[datetime] = None
    updated_at: Optional[datetime] = None
    last_login: Optional[datetime] = None

class UserProfileUpdate(BaseModel):
    display_name: Optional[str] = None
    learning_preferences: Optional[Dict[str, Any]] = None
    study_goals: Optional[List[str]] = None
    preferred_language: Optional[str] = None
    timezone: Optional[str] = None

class AgentResponse(BaseModel):
    agent_type: str = Field(..., description="Type of AI agent")
    response: Dict[str, Any] = Field(..., description="Agent response data")
    timestamp: str = Field(..., description="Response timestamp")

# Response Models
class StudyPlanResponse(BaseModel):
    plan_id: str
    title: str
    description: str
    topics: List[StudyTopic]
    total_estimated_duration: int
    progress_percentage: float
    created_at: datetime
    status: StudyPlanStatus

class LearningProgressResponse(BaseModel):
    total_study_time: int
    sessions_completed: int
    topics_completed: int
    current_streak: int
    longest_streak: int
    accuracy_percentage: float
    last_activity: Optional[datetime]

class FileListResponse(BaseModel):
    files: List[FileMetadata]
    total: int

class ProcessingStatusResponse(BaseModel):
    task_id: str
    status: ProcessingStatus
    progress_percentage: float
    result_data: Optional[Dict[str, Any]] = None
    error_message: Optional[str] = None
    created_at: datetime
    updated_at: datetime
