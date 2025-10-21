from storages.backends.s3boto3 import S3Boto3Storage
from config.settings import STATICFILES_LOCATION
import os
import uuid


class MediaStorage(S3Boto3Storage):
    location = 'media'
    file_overwrite = False

    def get_available_name(self, name, max_length=None):
        base, ext = os.path.splitext(name)
        unique_name = f"{base}_{uuid.uuid4().hex}{ext}"
        return super().get_available_name(unique_name, max_length)

class StaticStorage(S3Boto3Storage):
    location = STATICFILES_LOCATION