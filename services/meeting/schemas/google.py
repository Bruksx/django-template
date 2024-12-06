from dataclasses import dataclass
from datetime import datetime
from typing import Optional


@dataclass
class DateTime:
    dateTime: str
    timeZone: Optional[str] = None

@dataclass
class ConferenceSolutionKey:
    type: str


@dataclass
class CreateRequest:
    requestId: str
    conferenceSolutionKey: ConferenceSolutionKey

@dataclass
class ConferenceData:
    createRequest: CreateRequest
    notes: Optional[str]

@dataclass
class Attendee:
    email: str

@dataclass
class Meeting:
    summary: str
    description: str
    start: DateTime
    end: DateTime
    attendees: list[Attendee]
    conferenceData: Optional[ConferenceData] = None