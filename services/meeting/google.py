from services.meeting.base import IMeetingService
from services.meeting.schemas.common import MeetingSchema, MeetingResponseSchema
from services.meeting.schemas.google import Meeting, CreateRequest, Attendee, DateTime, ConferenceData, \
    ConferenceSolutionKey
from google.oauth2.credentials import Credentials
from googleapiclient.discovery import build

# Path to your service account JSON file

class GoogleService(IMeetingService):
    def __init__(self):
        self.SERVICE_ACCOUNT_FILE = 'path/to/your-credentials.json'
        self.SCOPES = ['https://www.googleapis.com/auth/calendar']

        self.credentials = {}

        self.service = {}

    def create_meeting(self, data: MeetingSchema, access_token)->MeetingResponseSchema:
        creds = Credentials(access_token)
        service = build("calendar", "v3", credentials=creds)
        event = Meeting(
            summary=data.topic,
            description=data.agenda,
            start=DateTime(dateTime=data.start_time.isoformat(), timeZone=data.timezone),
            end=DateTime(dateTime=data.end_time.isoformat(), timeZone=data.timezone),

            attendees=[Attendee(email=participant.email) for participant in data.participants]
        )
        event.conferenceData = ConferenceData(
            createRequest= CreateRequest(
                requestId=data.service_specific_data.google_meet_specific.request_id,
                conferenceSolutionKey=ConferenceSolutionKey(
                    type='hangoutsMeet'
                )
            ),
            notes=data.agenda
        )

        event = service.events().insert(
            calendarId="primary",
            body=event.__dict__,
            conferenceDataVersion=1
        ).execute()

        return MeetingResponseSchema(
            link=event.get('htmlLink'),
            url=event['conferenceData']['entryPoints'][0]['uri']
        )