# import os
#
# import django
#
#
# os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'config.settings')
# django.setup()
# from services.job_posting.services.lever_job_download import import_lever_jobs
# from jobs.schemas import JobPostFullDetailSchema
# from jobs.models import JobPost
# from core.schemas import GenericNameAndUidSchema
# from jobs.models import EmploymentType
#
#
#
#
# jobs = import_lever_jobs()
#
#
# for j in JobPost.objects.order_by("-id")[:30]:
#     try:
#         print(JobPostFullDetailSchema.from_orm(j).model_dump_json())
#     except Exception as e:
#         # print("error: ", e)
#         print("job: ", j)
#
#
# for j in EmploymentType.objects.all():
#     print(GenericNameAndUidSchema.from_orm(j).model_dump_json())