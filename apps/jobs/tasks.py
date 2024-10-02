from typing import List
from uuid import UUID

from django.conf import settings
from django.core.mail import send_mail, EmailMultiAlternatives
from django.template import loader

from accounts.models import Talent, User
from jobs.models import JobPost


def send_shared_job_email(job_post_id:int, talent_ids:List[UUID]=None, emails: List[str]=None):
    job_post = JobPost.objects.filter(id=job_post_id).select_related('job').first()
    if not job_post:
        raise Exception("Job post not found")
    template = loader.get_template('jobs/share_job.html')
    if emails:
        context = {
            'talent': "User",
            'job_title': job_post.job.title
        }
        html_content = template.render(context)

        email =EmailMultiAlternatives(
            subject='Shared Job Post',
            body=html_content,
            from_email=settings.DEFAULT_FROM_EMAIL,
            bcc=emails,
        )
        email.attach_alternative(html_content, "text/html")
        email.send()
    if talent_ids:
        users = User.objects.filter(talent__uid__in=talent_ids)
        for talent_user in users:
            context = {
                'talent': f"{talent_user.get_full_name()}",
                'job_title': job_post.job.title
            }
            html_content = template.render(context)

            email = EmailMultiAlternatives(
                subject='Shared Job Post',
                body=html_content,
                from_email=settings.DEFAULT_FROM_EMAIL,
                to=[talent_user.email],
            )
            email.attach_alternative(html_content, "text/html")
            email.send()
        return