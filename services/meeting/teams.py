from services.meeting.base import IMeetingService
from services.meeting.schemas.common import MeetingSchema, MeetingResponseSchema
from services.meeting.schemas.teams import Meeting, Attendee, EmailAddress, DateTime, Location, Body
from services.meeting.requestors.teams import TeamsRequestor

class TeamsMeetingService(IMeetingService):
    def __init__(self):
        self.service = {}

    def create_meeting(self, data:MeetingSchema)->MeetingResponseSchema:
        meeting = Meeting(
            subject=data.topic,
            allowNewTimeProposals=True,
            attendees=[
                Attendee(
                    emailAddress=EmailAddress(
                        address=participant.email,
                        name=participant.name),
                    type="required")
                for participant in data.participants],
            start=DateTime(
                dateTime=data.start_time.isoformat(),
                timeZone=data.timezone
            ),
            end=DateTime(dateTime=data.end_time.isoformat(),
            timeZone=data.timezone),
            location=Location(
                displayName=data.service_specific_data.teams_specific.display_name
            ),
            body=Body(
                contentType="HTML",
                content=data.agenda
            ),
            onlineMeetingProvider="teamsForBusiness",
            isOnlineMeeting=True,
        )
        url = "https://graph.microsoft.com/v1.0/me/onlineMeetings"
        response = TeamsRequestor().post(url, payload=meeting.__dict__).json()

        return MeetingResponseSchema(
            link=response.get('htmlLink'),
            url=response.get('startUrl')
        )


