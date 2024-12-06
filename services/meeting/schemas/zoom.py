from dataclasses import dataclass
from typing import List

from pydantic import EmailStr


@dataclass
class Invitee:
    email: EmailStr


@dataclass
class Settings:
    host_video: bool
    participant_video: bool
    join_before_host: bool
    mute_upon_entry: bool
    approval_type: int
    registration_type: int
    meeting_invitees: List[Invitee]



@dataclass
class Meeting:
    topic: str
    type: int
    start_time: str
    duration: int
    password: str
    timezone: str
    agenda: str
    default_password: bool
    settings: Settings