import json
from datetime import datetime, timedelta
from typing import Optional

import requests
from django.conf import settings
from django.utils import timezone

from helpers.loggers import Logger, LogSchema

BASE_URL = "https://apis.indeed.com"
AUTH_URL = f"{BASE_URL}/oauth/v2/tokens"
GRAPHQL_URL = f"{BASE_URL}/graphql"

CLIENT_ID = settings.INDEED_CLIENT_ID
CLIENT_SECRET = settings.INDEED_CLIENT_SECRET

class IndeedJobPostingService:

    def __init__(self):
        self.access_token:Optional[str] = None
        self.expiry_date:Optional[datetime] = None

    def __update_access_token__(self):
        if self.expiry_date and self.expiry_date.__gt__(timezone.now()) and self.access_token:
            return
        return self.__set_access_token__()

    def __set_access_token__(self):
        headers = {
            'Content-Type': 'application/x-www-form-urlencoded',
            'Accept': 'application/json'
        }
        data = {
            'grant_type': 'client_credentials',
            'client_id': CLIENT_ID,
            'client_secret': CLIENT_SECRET,
            'scope': 'employer_access'
        }
        try:
            response = requests.post(AUTH_URL, headers=headers, data=data).json()
            """
                {
                  "access_token": "eyJraWQiOiI1OTdjYTgxNC0YdVBLkWfA",
                  "scope": "employer_access",
                  "token_type": "Bearer",
                  "expires_in": 3600
                }
            """
            self.access_token = response["access_token"]
            self.expiry_date = timezone.now() + timedelta(seconds=int(response["expires_in"]))
        except requests.exceptions.RequestException as e:
            Logger.error(LogSchema(
                sender="IndeedJobPostingService",
                title="unable to retrieve access token",
                description=str(e),
            ).__dict__, exc_info=True)

    def expire_jobs(self, job_posts):
        from services.job_posting.services.indeed import convert_job_object_to_indeed_id

        mutation = """
        mutation {
          jobsIngest {
            expireSourcedJobsBySourcedPostingId(input: { jobs: $jobs }) {
              results {
                trackingKey
              }
            }
          }
        }
        """
        self.__update_access_token__()
        headers = {
            'Content-Type': 'application/json',
            'Accept': 'application/json',
            'Authorization': f'Bearer {self.access_token}'
        }
        job_posts = map(convert_job_object_to_indeed_id, job_posts)
        payload = {'query': mutation, 'variables': {"jobs": job_posts}}
        try:
            response = requests.post(GRAPHQL_URL, headers=headers, json=payload)
            response.raise_for_status()

        except (requests.exceptions.RequestException, json.JSONDecodeError) as e:
            Logger.error(LogSchema(
                sender="IndeedJobPostingService",
                title="unable to delete jobs",
                description=str(e),
            ).__dict__, exc_info=True)

    def create_jobs(self, job_posts):
        from services.job_posting.services.indeed import convert_job_object_to_job

        self.__update_access_token__()
        headers = {
            'Content-Type': 'application/json',
            'Accept': 'application/json',
            'Authorization': f'Bearer {self.access_token}'
        }
        job_posts = map(convert_job_object_to_job, job_posts)
        mutation = """
        mutation {
          jobsIngest {
            createSourcedJobPostings(input: { $jobPostings }) {
              results {
                jobPosting {
                  sourcedPostingId
                }
              }
            }
          }
        """
        payload = {'query': mutation, 'variables': {"jobPostings": job_posts}}
        try:
            response = requests.post(GRAPHQL_URL, headers=headers, json=payload)
            response.raise_for_status()
            data = response.json()
            index = 0
            for job_post in job_posts:
                sourced_posting_id = data['data']['jobsIngest']['createSourcedJobPostings']['results'][index]['jobPosting'][
                    'sourcedPostingId']
                job_post.update(indeed_id=sourced_posting_id)
                index+=1


        except (requests.exceptions.RequestException,json.JSONDecodeError ) as e:
            Logger.error(LogSchema(
                sender="IndeedJobPostingService",
                title="unable to create jobs",
                description=str(e),
            ).__dict__, exc_info=True)

    def update_jobs(self, job_posts):
        from services.job_posting.services.indeed import convert_job_object_to_job
        self.__update_access_token__()
        headers = {
            'Content-Type': 'application/json',
            'Accept': 'application/json',
            'Authorization': f'Bearer {self.access_token}'
        }
        job_posts = map(convert_job_object_to_job, job_posts)
        mutation = """
        mutation {
          jobsIngest {
            updateSourcedJobPostings(input: { $jobPostings }) {
              results {
                jobPosting {
                  sourcedPostingId
                }
              }
            }
          }
        """
        payload = {'query': mutation, 'variables': {"jobPostings": job_posts}}
        try:
            response = requests.post(GRAPHQL_URL, headers=headers, json=payload)
            response.raise_for_status()

        except (requests.exceptions.RequestException,json.JSONDecodeError ) as e:
            Logger.error(LogSchema(
                sender="IndeedJobPostingService",
                title="unable to update jobs",
                description=str(e),
            ).__dict__, exc_info=True)



indeed_job_posting_service = IndeedJobPostingService()