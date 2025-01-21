from storages.backends.s3boto3 import S3Boto3Storage
from config.settings import STATICFILES_LOCATION


class MediaStorage(S3Boto3Storage):
    location = 'media'
    file_overwrite = False

class StaticStorage(S3Boto3Storage):
    location = STATICFILES_LOCATION