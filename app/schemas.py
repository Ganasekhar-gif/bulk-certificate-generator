from pydantic import BaseModel, ConfigDict, EmailStr, Field
from datetime import datetime
from typing import List, Optional
from app.models import JobStatus, CertificateStatus


class RecipientCreate(BaseModel):
    name: str = Field(..., min_length=1, max_length=255, description="Recipient's full name")
    email: EmailStr = Field(..., description="Recipient's email address")
    course_name: str = Field(..., min_length=1, max_length=255, description="Name of the course/event")
    completion_date: str = Field(..., min_length=1, max_length=50, description="Date of completion")


class JobCreate(BaseModel):
    recipients: List[RecipientCreate] = Field(
        ...,
        min_length=1,
        max_length=1000,
        description="List of recipients (minimum 1, maximum 1000 per job)",
    )


class CertificateResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    recipient_name: str
    recipient_email: str
    course_name: str
    completion_date: str
    status: CertificateStatus
    certificate_path: Optional[str] = None
    error_message: Optional[str] = None
    created_at: datetime


class JobResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    status: JobStatus
    total_recipients: int
    successful_count: int
    failed_count: int
    created_at: datetime
    completed_at: Optional[datetime] = None
    error_message: Optional[str] = None
    certificates: List[CertificateResponse] = []


class JobStatusResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    status: JobStatus
    total_recipients: int
    successful_count: int
    failed_count: int
    created_at: datetime
    completed_at: Optional[datetime] = None
    error_message: Optional[str] = None
