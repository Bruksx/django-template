from dataclasses import dataclass
from datetime import datetime
from typing import List, Optional, Protocol

from ninja import Schema
from pydantic import EmailStr


class ParticipantSchema(Protocol):
    """Schema for meeting participants."""
    email: EmailStr
    name: Optional[str] = None

class MeetingSettingsSchema(Protocol):
    """Schema for advanced meeting settings."""
    host_video: Optional[bool] = None
    participant_video: Optional[bool] = None
    join_before_host: Optional[bool] = None
    mute_upon_entry: Optional[bool] = None
    approval_type: Optional[int] = None
    registration_type: Optional[int] = None

class GoogleSpecificDataSchema(Protocol):
    """Schema for Google-specific meeting data."""
    calendar_id: Optional[str] = None
    request_id: Optional[str] = None

class TeamsSpecificDataSchema(Protocol):
    """Schema for Microsoft Teams-specific meeting data."""
    display_name: str

class ServiceSpecificDataSchema(Protocol):
    """Schema for service-specific meeting data."""
    zoom_specific: Optional[dict] = None
    teams_specific: Optional[TeamsSpecificDataSchema] = None
    google_meet_specific: Optional[GoogleSpecificDataSchema] = None

class MeetingSchema(Protocol):
    """Unified schema for scheduling meetings across services."""
    topic: str
    start_time: datetime
    agenda: Optional[str] = None
    end_time: Optional[datetime] = None
    duration: Optional[int] = None
    timezone: Optional[str] = None
    participants: Optional[List[ParticipantSchema]] = None
    settings: Optional[MeetingSettingsSchema] = None
    service_specific_data: Optional[ServiceSpecificDataSchema] = None


@dataclass
class MeetingResponseSchema:
    """Schema for meeting responses."""
    link: Optional[str]
    url: Optional[str]