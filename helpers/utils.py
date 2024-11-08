import base64
import random
import string
import uuid
from typing import Optional

from django.core.files.base import ContentFile
from ninja.responses import Response

from helpers.loggers import Logger


def success_response(message="successful", data=None, status=200):
    return Response(data={"message": message, "data": data|dict()}, status=status)

def failure_response(message="failed", status=400):
    return Response(data={"message": message, "data": dict()}, status=status)

def is_valid_uuid(value):
    try:
        uuid.UUID(str(value))
        return True
    except ValueError:
        return False

def convert_base64_to_image_file(base64_string, * ,name=None)->Optional[ContentFile]:
    if not name:
        letters_and_digits = string.ascii_letters + string.digits
        name = ''.join(random.choice(letters_and_digits) for _ in range(10))
    try:
        file_content= base64.b64decode(base64_string)
        return ContentFile(file_content, name=name)
    except Exception as e:
        Logger.error(dict(
            sender="Helper Utils",
            title="Error converting base64 image to file",
            descrition=str(e)
        ), exc_info=True)





