from enum import Enum
from typing import Optional, Any

from attr import dataclass
from django.db.backends.base.base import logger

import json


class LogType(Enum):
	CRITICAL = 50
	ERROR = 40
	WARNING = 30
	INFO = 20
	DEBUG = 10


@dataclass
class LogSchema:
	sender: str
	title: str
	description: Optional[str] = None
	data: Optional[Any] = None

class Logger:

	name = "GTC Logger"

	@classmethod
	def __execute_function(cls, log_type:LogType, msg:dict,  *args, **kwargs):
		from helpers.email.utils import send_email

		try:

			msg = LogSchema(**msg)
			# we can do whatever here to handle the log.
			# For example: we can send the log to a file or a database
			if kwargs.get("email"):
				send_email(
					subject=f"{cls.name} ({log_type.name})",
					plain_body=f"""
					Sender: {msg.sender}
					Title: {msg.title}
					Description: {msg.description}
					Data: {json.dumps(msg.data) if isinstance(msg.data, dict) else msg.data}
					""",
					emails=[kwargs.get("email")],
					from_user="GTC Logger",
				)
			return logger.log(log_type.value, f"{cls.name} ({log_type.name}): {msg.__dict__}", *args, **kwargs)
		except TypeError as e:
			cls.critical(dict(
				sender="Logger",
				title=f"Incorrect log schema",
				description=str(e)
			), *args, **kwargs)
		return


	@classmethod
	def critical(cls, msg:dict, *args, **kwargs):
		cls.__execute_function(LogType.CRITICAL, msg, *args, **kwargs)

	@classmethod
	def error(cls, msg:dict, *args, **kwargs):
		cls.__execute_function(LogType.ERROR, msg, *args, **kwargs)

	@classmethod
	def warning(cls, msg:dict, *args, **kwargs):
		cls.__execute_function(LogType.WARNING, msg, *args, **kwargs)

	@classmethod
	def info(cls, msg:dict, *args, **kwargs):
		cls.__execute_function(LogType.INFO, msg, *args, **kwargs)

	@classmethod
	def debug(cls, msg:dict, *args, **kwargs):
		cls.__execute_function(LogType.DEBUG, msg, *args, **kwargs)


