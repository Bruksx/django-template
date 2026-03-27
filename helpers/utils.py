import base64
import hashlib
import json
import logging
import os
import random
import re
import string
import sys
import traceback
import uuid
from datetime import timezone, time, datetime
from html import unescape
from io import BytesIO
from sys import getsizeof
from typing import Optional, List
from urllib.parse import urlencode, urljoin
from zoneinfo import ZoneInfo

import bleach
import boto3
import ijson
import pdfkit
import psutil
from botocore.exceptions import NoCredentialsError
from cryptography.fernet import Fernet
from django.conf import settings
from django.core.files.base import ContentFile
from django.db.models import QuerySet
from django.http import HttpResponse
from django.utils import timezone
from ninja.errors import HttpError
from openpyxl import Workbook
from openpyxl.styles import Font

from helpers.decorators import test_env_decorator
from helpers.loggers import Logger
from monkeypatches.response import Response


def create_url_with_params(base_url: str, params: dict, doseq: bool = False) -> str:
    """
    Constructs a URL by appending URL-encoded parameters to a base URL.

    Args:
        base_url (str): The base URL (e.g., "https://api.example.com/data").
        params (dict): A dictionary of parameters where keys are parameter names
                       and values are the parameter values. Values can be single
                       items or lists/tuples if doseq is True.
        doseq (bool): If True, and a parameter's value is a sequence (e.g., list),
                      multiple key=value pairs will be generated (e.g., param=a&param=b).
                      If False, sequences will be treated as a single string.
                      Defaults to False.

    Returns:
        str: The full URL with correctly encoded parameters.
    """
    if not isinstance(base_url, str):
        raise TypeError("base_url must be a string.")
    if not isinstance(params, dict):
        raise TypeError("params must be a dictionary.")

    # Encode the parameters
    encoded_params = urlencode(params, doseq=doseq)

    # Combine the base URL and the encoded query string
    # urljoin is robust for correctly adding '?' and handling existing query strings
    full_url = urljoin(base_url, '?' + encoded_params)

    return full_url

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

    if "test" in sys.argv:
        return True

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
        url = f"https://{bucket}.s3.amazonaws.com/"
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
                              description=f"Failed to delete S3 object {key}: {str(e)}"), exc_info=True)
        raise  # Just 'raise' to preserve stack trace


@test_env_decorator(["https://s3.amazonaws.com/ample.jpg"])
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


def to_utc(time_: str|time , tzinfo="America/Vancouver"):
    """
    Converts a local time string to a UTC time object.

    Args:
        time_str (str): Time string in "HH:MM:SS" format (24-hour clock).
        tzinfo (str, optional): IANA timezone name representing the local time zone.
            Defaults to "America/Vancouver".

    Returns:
        datetime.time: The equivalent UTC time as a time object (without date).

    Example:
        >>> to_utc("08:00:00", tzinfo="America/Vancouver")
        datetime.time(15, 0)  # (e.g. if DST is in effect)

    Notes:
        - The conversion is based on the current date.
        - The output is a naive `time` object in UTC.
    """
    today = datetime.now().date()
    if isinstance(time_, str):
        time_obj = datetime.strptime(time_, "%H:%M:%S").time()
    else:
        time_obj = time_
    date_time = datetime.combine(today, time_obj, tzinfo=ZoneInfo(tzinfo))
    utc_dt = date_time.astimezone(ZoneInfo("UTC"))
    return utc_dt.time()


def read_json_generator(file_path):
    """
    Generator function to read a JSON file and yield each object one at a time without loading the entire file into memory.

    Args:
        file_path (str): Path to the JSON file

    Yields:
        dict: Individual JSON object from the file

    Raises:
        FileNotFoundError: If the specified file doesn't exist
        ijson.JSONError: If the JSON is invalid
    """
    try:
        with open(file_path, 'r', encoding='utf-8') as file:
            # Parse JSON objects iteratively
            parser = ijson.items(file, 'item')
            for item in parser:
                yield item

    except FileNotFoundError:
        raise FileNotFoundError(f"File not found: {file_path}")
    except ijson.JSONError as e:
        raise ijson.JSONError(f"Invalid JSON format: {str(e)}")


def capitalize_bracketed(text):
    def replacer(match):
        content = match.group(1)
        # Only capitalize if no spaces inside
        if ' ' in content:
            return f"({content})"
        return f"({content.upper()})"

    return re.sub(r'\((.*?)\)', replacer, text)

def uppercase_first_word(text):
    # Strip leading/trailing spaces first
    text = text.strip()
    # Match a single word followed by optional space and a bracketed phrase
    pattern = r'^(\w+)\s*(\([^)]*\))$'
    return re.sub(pattern, lambda m: m.group(1).upper() + " " + m.group(2), text)



def alert_bug_via_email(func, default, *args, **kwargs):
    from helpers.email.utils import send_email
    try:
        return func(*args, **kwargs)
    except Exception as e:
        logging.error(str(e), exc_info=True)
        send_email(
            subject="Alert via Email",
            plain_body=str(traceback.format_exc()),
            emails=["ohaegbulouis@gmail.com"],
            from_user="1840",
        )
        return default

def sanitize_html_secure(html: str) -> str:
    """
    Security-focused HTML sanitizer:
    - Removes all scripts, iframes, embeds, objects
    - Removes all event handlers (onclick, onload, etc.)
    - Removes javascript: URLs
    - Leaves harmless HTML tags intact
    - Leaves CSS styles intact since they are not security threats
    """
    html = re.sub(r'<script\b[^>]*>.*?</script>', '', html, flags=re.IGNORECASE | re.DOTALL)

    # Only allow these harmless tags
    allowed_tags = {
        "p", "b", "i", "u", "strong", "em", "a"
        "ul", "ol", "li", "br", "span", "blockquote", "pre", "code"
    }

    # Allow only safe attributes
    allowed_attrs = {
        "*": ["style"],  # keep styles
        "a": ["href", "title", "target", "rel"]
    }

    # Sanitize with bleach
    cleaned = bleach.clean(
        html,
        tags=allowed_tags,
        attributes=allowed_attrs,
        protocols={"http", "https", "mailto"},  # no javascript: URLs
        strip=True,
        strip_comments=True
    )

    return cleaned

def html_to_text(html: str) -> str:
    """
    Converts HTML to plain text in a very fast way suitable for millions of records.

    Rules:
        - <br>, <p> -> newline
        - <li> -> "- " prefix
        - <a href="">text</a> -> text (URL)
        - Strips all other tags
    """
    if not html:
        return ""

    # 1. Handle links: <a href="URL">text</a> -> text (URL)
    html = re.sub(
        r'<a\s+[^>]*href=["\'](.*?)["\'][^>]*>(.*?)</a>',
        lambda m: f"{m.group(2)} ({m.group(1)})",
        html,
        flags=re.IGNORECASE | re.DOTALL
    )

    # 2. Convert <br> and <p> to newline
    html = re.sub(r'<br\s*/?>', '\n', html, flags=re.IGNORECASE)
    html = re.sub(r'</p\s*>', '\n', html, flags=re.IGNORECASE)
    html = re.sub(r'<p\s*>', '', html, flags=re.IGNORECASE)

    # 3. Convert <li> to "- "
    html = re.sub(r'<li\s*>', '- ', html, flags=re.IGNORECASE)
    html = re.sub(r'</li\s*>', '\n', html, flags=re.IGNORECASE)

    # 4. Remove all remaining HTML tags
    html = re.sub(r'<[^>]+>', '', html)

    # 5. Unescape HTML entities
    html = re.sub(r'&nbsp;', ' ', html)
    html = re.sub(r'&amp;', '&', html)
    html = re.sub(r'&lt;', '<', html)
    html = re.sub(r'&gt;', '>', html)
    html = re.sub(r'&quot;', '"', html)
    html = re.sub(r'&#39;', "'", html)

    # 6. Normalize whitespace and strip
    lines = [line.strip() for line in html.splitlines()]
    return '\n'.join([unescape(line) for line in lines if line])


class Secret:
    @staticmethod
    def __derive_key__() -> bytes:
        from config.settings import SECRET_KEY
        # Convert your app secret into a 32-byte key
        return base64.urlsafe_b64encode(
            hashlib.sha256(SECRET_KEY.encode()).digest()
        )

    @classmethod
    def encrypt_dict(cls, data: dict) -> str:
        key = cls.__derive_key__()
        f = Fernet(key)
        json_data = json.dumps(data).encode()
        encrypted = f.encrypt(json_data)
        return encrypted.decode()

    @classmethod
    def decrypt_dict(cls, token: str) -> Optional[dict]:
        try:
            key = cls.__derive_key__()
            f = Fernet(key)
            decrypted = f.decrypt(token.encode())
            return json.loads(decrypted.decode())
        except Exception:
            return None

def export_rows_to_excel(rows:List[list], headers: list[str], title:str, bold_rows:List[int]=None, background=True):
    from core.models import Exports
    wb = Workbook()
    ws = wb.active
    ws.title = title

    ws.append(headers)
    header_length = len(headers)
    column_widths = {string.ascii_uppercase[i]: 0 for i in range(header_length)}
    mapper = {i: string.ascii_uppercase[i] for i in range(header_length)}
    for row in rows:
        for i, cell in enumerate(row):
            column_widths[mapper[i]] = max(column_widths[mapper[i]], len(str(cell)))
        ws.append(row)

    for col, width in column_widths.items():
        ws.column_dimensions[col].width = width + 3

    if bold_rows:
        for row in bold_rows:
            for cell in ws[row]:
                cell.font = Font(bold=True)

    output = BytesIO()
    wb.save(output)
    output.seek(0)
    timestamp = timezone.now().strftime("%B %d, %Y at %I:%M %p")
    filename = f"{title.replace(' ', '_').lower()}_{timestamp}.xlsx"
    if background is True:
        export = Exports()
        export.file.save(
            filename,
            ContentFile(output.read()),
            save=True
        )

        return export.file.url
    response = HttpResponse(
        content_type="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet"
    )
    response["Content-Disposition"] = f'attachment; filename="{filename}"'

    wb.save(response)
    return response
