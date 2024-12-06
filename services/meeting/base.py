from abc import ABC, abstractmethod

from services.meeting.schemas.common import MeetingSchema, MeetingResponseSchema


class IMeetingService(ABC):

    @abstractmethod
    def create_meeting(self, meeting:MeetingSchema)->MeetingResponseSchema:
        raise NotImplementedError

