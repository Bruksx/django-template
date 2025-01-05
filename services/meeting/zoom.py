from services.meeting.base import IMeetingService
from services.meeting.schemas.common import MeetingSchema, MeetingResponseSchema
from services.meeting.schemas.zoom import Meeting, Settings, Invitee
from services.meeting.requestors.zoom import ZoomRequestor


class ZoomService(IMeetingService):

    def __init__(self):
        self.service = {}

    def create_meeting(self, data:MeetingSchema) ->MeetingResponseSchema:
        user_id = "me"
        url = f"https://api.zoom.us/v2/users/{user_id}/meetings"
        meeting = Meeting(
            topic=data.topic,
            type=2,
            start_time=data.start_time.isoformat(),
            duration=data.duration,
            timezone=data.timezone,
            agenda=data.agenda,
            settings=Settings(
                host_video=data.settings.host_video,
                participant_video=data.settings.participant_video,
                join_before_host=data.settings.join_before_host,
                mute_upon_entry=data.settings.mute_upon_entry,
                approval_type=data.settings.approval_type,
                registration_type=data.settings.registration_type,
                meeting_invitees = [Invitee(email=participant.email) for participant in data.participants]
            ),
            password="Password",
            default_password=False
        )
        response = ZoomRequestor.post(url, payload=meeting.__dict__)
        event = response.json()
        """event = self.service.meetings().create(
            body=meeting.__dict__,
            conferenceId=data.service_specific_data.zoom_meet_specific.conference_id
        ).execute()"""

        return MeetingResponseSchema(link=event.get('joinUrl'), url=event.get('startUrl'))