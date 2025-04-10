from datetime import datetime, timedelta
from typing import Optional, List

import requests

from config import settings
from helpers.loggers import Logger
from services.job_posting.enums.linkedIn import OperationTypeEnum
from services.job_posting.schema.linkedIn import AccessTokenSchema, JobSchema


class LinkedInJobPostingService:
	def __init__(self):
		self.__access_token__:Optional[AccessTokenSchema] = None
		self.__client_secret__ = settings.LINKEDIN_CLIENT_SECRET
		self.__client_id__ = settings.LINKEDIN_CLIENT_ID
		Logger.info(msg={
			"sender": "LinkedIn Job Posting service",
			"title": "LinkedIn Job Posting service init",
			"description": "LinkedIn Job Posting service init"
		})


	def __set_access_token__(self):
		try:
			url = "https://www.linkedin.com/oauth/v2/accessToken"
			grant_type = "client_credentials"

			post_data = {
				"grant_type": grant_type,
				"client_id": self.__client_id__,
				"client_secret": self.__client_secret__
			}
			headers = {
				"Content-Type": "application/x-www-form-urlencoded"
			}
			response = requests.post(url=url, headers=headers, data=post_data)
			if response.status_code != 200:
				Logger.critical(msg={
					"sender": "LinkedIn Job Posting service",
					"title": "LinkedIn Token Error",
					"description": response.text
				})
				return

			json_data = response.json()
			self.__access_token__ =AccessTokenSchema(token=json_data["access_token"],
													 expires_in=datetime.now() + timedelta(json_data["expires_in"]))
		except Exception as e:
			Logger.critical(msg={
				"sender": "LinkedIn Job Posting service",
				"title": "LinkedIn Token Error",
				"description": str(e)
			}, exc_info=True)
			return

	def __refresh_access_token__(self):
		if self.__access_token__ is None:
			self.__set_access_token__()
		elif self.__access_token__.expires_in.__lt__(datetime.now()):
			self.__set_access_token__()
		return

	def call_endpoint(self, jobs:List[JobSchema], operation_type:OperationTypeEnum):
		if len(jobs) == 0:
			return
		self.__refresh_access_token__()
		if not self.__access_token__:
			return
		try:
			url = "https://api.linkedin.com/v2/simpleJobPostings"
			headers = {
				"Authorization": f"Bearer {self.__access_token__.token}",
				"x-restli-method": "batch_create"
			}
			job_data = {
				 "elements": [dict(**job.__dict__, jobPostingOperationType=operation_type.value)
				              for job in jobs ]
			}
			response = requests.post(url=url, headers=headers, json=job_data)
			response_json = response.json()
			if "elements" not in response_json:
				Logger.critical(msg={
					"sender": "LinkedIn Job Posting service",
					"title": f"LinkedIn Job {operation_type.value.title()} Error",
					"description": response.text
				})
				return
			for element in response_json["elements"]:
				if element["status"] != 202:
					Logger.critical(msg={
						"sender": "LinkedIn Job Posting service",
						"title": f"LinkedIn Job {operation_type.value.title()} Error",
						"description": element["error"]["message"]
					})
					return
				# do something with job id
				Logger.info(msg={
					"sender": "LinkedIn Job Posting service",
					"title": "LinkedIn Job Creation Success",
					"description": element["id"]
				})
		except Exception as e:
			Logger.critical(msg={
				"sender": "LinkedIn Job Posting service",
				"title": f"LinkedIn Job {operation_type.value.title()} Error",
				"description": str(e)
			}, exc_info=True)
			return


linked_job_posting_service = LinkedInJobPostingService()