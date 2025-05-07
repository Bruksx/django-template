import base64
import os
import random
import re
import string
import uuid
from datetime import timezone
from io import BytesIO
from sys import getsizeof
from typing import Optional, List

import boto3
import pdfkit
import psutil
from botocore.exceptions import NoCredentialsError
from django.conf import settings
from django.core.files.base import ContentFile
from django.db.models import QuerySet
from ninja.errors import HttpError

from helpers.loggers import Logger
from monkeypatches.response import Response


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

def convert_base64_to_image_file(base64_string, name=None)->Optional[ContentFile]:
    if not base64_string:
        return
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
            description=str(e)
        ), exc_info=True)

def html_to_pdf(html: str):
    try:
        pdf_file = pdfkit.from_string(
            html,
            False,
            options={"enable-local-file-access": "",
                     'print-media-type': True
                     },
        )
        return pdf_file
    except OSError as e:
        Logger.error(dict(
            sender="Helper Utils",
            title="HTML TO PDF OS Error",
            description=str(e)
        ))
        return

def html_to_pdf3(source_html):
    try:
        # Create a BytesIO object to store the PDF output.
        pdf_output = BytesIO()

        # Use xhtml2pdf to convert the HTML content to a PDF and store it in pdf_output.
        pisa.CreatePDF(source_html, dest=pdf_output, encoding='UTF-8')

        # Return the BytesIO object containing the PDF data.
        return pdf_output

    except Exception as e:
        print(f"Error during PDF conversion: {e}")
        return None


def delete_s3_item(key):
    from boto3.session import Session

    if not settings.USE_AWS_S3:
        Logger.info(msg=dict(sender="Helper Utils", title="AWS S3 DELETE Info",
                             description='AWS S3 not enabled in settings, skipping delete'))
        return

    try:
        region = settings.AWS_S3_REGION_NAME
        session = Session(
            aws_access_key_id=settings.AWS_ACCESS_KEY_ID,
            aws_secret_access_key=settings.AWS_SECRET_ACCESS_KEY,
            region_name=region
        )
        s3 = session.resource("s3")
        bucket = settings.AWS_STORAGE_BUCKET_NAME
        url = f"https://{bucket}.s3.{region}.amazonaws.com/"
        if str(key).startswith(url):
            key = key.split(url)[-1]

        obj = s3.Object(bucket, key)

        # Verify object exists before deleting
        try:
            obj.load()
        except Exception as load_error:
            Logger.error(msg=dict(sender="Helper Utils", title="AWS S3 DELETE Error",
                                 description=f"Object not found: {key}. Error: {str(load_error)}"))
            return False

        # Perform deletion
        obj.delete()
        Logger.info(msg=dict(sender="Helper Utils", title="AWS S3 DELETE Info",
                             description=f"Successfully deleted S3 object: {key}"))
        return True

    except Exception as e:
        Logger.error(msg=dict(sender="Helper Utils", title="AWS S3 DELETE Error",
                              description=f"Failed to delete S3 object {key}: {str(e)}", exc_info=True), exc_info=True)
        raise  # Just 'raise' to preserve stack trace

def upload_to_s3(files, folder_name):
    if not settings.USE_AWS_S3:
        return
    if not isinstance(files, list):
        files = [files]
    bucket_name = settings.AWS_STORAGE_BUCKET_NAME
    region = settings.AWS_S3_REGION_NAME
    s3_client = boto3.client(
        "s3",
        aws_access_key_id=settings.AWS_ACCESS_KEY_ID,
        aws_secret_access_key=settings.AWS_SECRET_ACCESS_KEY,
        region_name=region,
    )

    uploaded_urls = []

    for file in files:
        try:
            file_key = f"{folder_name}/{file.name}"
            s3_client.upload_fileobj(
                file,  # File object
                bucket_name,  # Bucket name
                file_key,  # Key in S3
            )

            file_url = f"https://{bucket_name}.s3.{region}.amazonaws.com/{file_key}"
            uploaded_urls.append(file_url)

        except NoCredentialsError:
            raise Exception("AWS credentials not available")
        except Exception as e:
            raise Exception(f"Failed to upload file {file.name}: {str(e)}")

    return uploaded_urls if len(uploaded_urls) > 1 else uploaded_urls[0]

def upload_to_server(files, folder_name):
    if not isinstance(files, list):
        files = [files]

    saved_paths = []

    for file in files:
        try:
            # Create the directory if it doesn't exist
            save_path = os.path.join(settings.MEDIA_ROOT, folder_name)
            os.makedirs(save_path, exist_ok=True)

            # Save the file
            file_path = os.path.join(save_path, file.name)
            with open(file_path, 'wb+') as destination:
                for chunk in file.chunks():
                    destination.write(chunk)

            # Append the relative file path
            relative_path = os.path.join(settings.MEDIA_URL, folder_name, file.name)
            saved_paths.append(f"{settings.WEB_URL}{relative_path}".replace("\\", "/"))

        except Exception as e:
            raise Exception(f"Failed to save file {file.name}: {str(e)}")

    return saved_paths if len(saved_paths) > 1 else saved_paths[0]

def calculate_chunk_size(queryset_sample, memory_fraction=0.05, default_record_size_kb=3):
    """
    Calculate an optimal chunk size for processing a queryset based on available memory.

    Parameters:
        queryset_sample (QuerySet): A small sample queryset to estimate record size.
        memory_fraction (float): Fraction of available memory to use (default: 5%).
        default_record_size_kb (int): Default size in KB to assume per record if sample estimation fails.

    Returns:
        int: Optimal chunk size.
    """
    try:
        # Estimate the size of a single record
        sample_record = queryset_sample.first()
        record_size = getsizeof(sample_record) if sample_record else default_record_size_kb * 1024
    except Exception:
        # Fallback to default record size if sample fails
        record_size = default_record_size_kb * 1024

    # Get available memory
    memory_info = psutil.virtual_memory()
    available_memory = memory_info.available * memory_fraction  # Use a fraction of available memory

    # Calculate chunk size
    chunk_size = int(available_memory / record_size)
    return max(chunk_size, 1)  # Ensure at least one record per chunk

def chunk_queryset(queryset: QuerySet):
    """Yield chunks of a queryset for memory efficiency."""
    start = 0
    chunk_size = calculate_chunk_size(queryset)
    while True:
        chunk = list(queryset[start:start + chunk_size])
        if not chunk:
            break
        yield chunk
        start += chunk_size

def is_valid_email(email):
  """
  Checks if the given string is a valid email address.

  Args:
    email: The string to be checked.

  Returns:
    True if the string is a valid email address, False otherwise.
  """
  email_regex = r"^[a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,}$"
  return re.match(email_regex, email) is not None

def validate_password(password):
    if not password:
        raise HttpError(400, 'Password cannot be null')

    if len(password) < 8:
        raise HttpError(400, 'Password must be at least 8 characters long')

    if not any(char.isdigit() for char in password):
        raise HttpError(400, 'Password must contain at least one digit.')

    if not any(char.isalpha() for char in password):
        raise HttpError(400, 'Password must contain at least one letter.')

    if not any(char.isupper() for char in password):
        raise HttpError(400, 'Password must contain at least one uppercase letter.')

    if not any(char in '!@#$%^&*()_+=-[]{}|;:,.<>?' for char in password):
        raise HttpError(400, 'Password must contain at least one special character.')


def prepare_for_json(data):
    new_data = {}
    for key, value in data.items():
        if isinstance(value, uuid.UUID):
            new_data[key] = str(value)
        elif isinstance(value, dict):
            new_data[key] = prepare_for_json(value)
        elif isinstance(value, list):
            new_list = []
            for item in value:
                if isinstance(item, uuid.UUID):
                    new_list.append(str(item))
                elif isinstance(item, dict):
                    new_list.append(prepare_for_json(item))
                else:
                    new_list.append(item)
            new_data[key] = new_list
        else:
            new_data[key] = value
    return new_data


def datetime_to_epoch_milliseconds(dt)->int:
  if dt.tzinfo is None:
    # If the datetime object has no timezone information, assume it's in local time.
    dt = dt.replace(tzinfo=timezone.utc)
  else:
    # Convert the datetime object to UTC.
    dt = dt.astimezone(timezone.utc)

  return int(dt.timestamp() * 1000)


def sort_params_function(sorts:List[str], mapper:dict[str, str])->List[str]:
    sort_values = list()
    for sort in sorts:
        sort_sign = "-" if sort.startswith("-") else ""
        sort = sort[1:] if sort.startswith("-") else sort
        sort_value = mapper.get(sort)
        if sort_value:
            sort_values.append(f"{sort_sign}{sort_value}")
    return sort_values