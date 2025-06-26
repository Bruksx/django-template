# import os
# from random import choice
#
# import django
#
# os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'config.settings')
# django.setup()
#
# from jobs.models import JobPost
# from jobs.enums import JobStatusType
#
#
#
#
#
# jobs = JobPost.objects.iterator()
# for job in jobs:
#     job.status = choice(JobStatusType.values())
#     job.save()
#
#
