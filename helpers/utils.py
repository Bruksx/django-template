import logging
import uuid
from typing import Optional

from ninja.responses import Response
import base64
from django.core.files.base import ContentFile
import random
import string



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

def convert_base64_to_file(base64_string, * ,name=None)->Optional[ContentFile]:
    if not name:
        letters_and_digits = string.ascii_letters + string.digits
        name = ''.join(random.choice(letters_and_digits) for _ in range(10))
    try:
        file_content= base64.b64decode(base64_string)
        return ContentFile(file_content, name=name)
    except Exception as e:
        logging.critical(f"Error converting base64 to file: {e}", exc_info=True)
        return None


