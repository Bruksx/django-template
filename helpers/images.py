import base64
from io import BytesIO
from PIL import Image
from django.core.files.base import ContentFile
import random
import string


def convert_base64_to_image_file(base64_string, * ,name=None):
    if not name:
        letters_and_digits = string.ascii_letters + string.digits
        name = ''.join(random.choice(letters_and_digits) for _ in range(10))
    image_file= base64.b64decode(base64_string)
    image_content_file = ContentFile(image_file, name=name)
    return image_content_file