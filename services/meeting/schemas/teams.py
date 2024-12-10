from dataclasses import dataclass
from typing import List

from pydantic import EmailStr


@dataclass
class Body:
    content: str
    contentType: str

@dataclass
class Location:
    displayName: str

@dataclass
class DateTime:
    dateTime: str
    timeZone: str

@dataclass
class EmailAddress:
    address: EmailStr
    name: str

@dataclass
class Attendee:
    emailAddress: EmailAddress
    type: str



@dataclass
class Meeting:
    subject: str
    body: Body
    start: DateTime
    end: DateTime
    location: Location
    attendees: List[Attendee]
    allowNewTimeProposals: bool
    isOnlineMeeting: bool
    onlineMeetingProvider: str