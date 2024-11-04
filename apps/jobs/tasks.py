from typing import List
from uuid import UUID

from django.conf import settings
from django.core.mail import send_mail, EmailMultiAlternatives
from django.db.models import Q
from django.template import loader

from accounts.enums import UserType
from accounts.models import Talent, User
from chats.models import Conversation, Message
from jobs.models import JobPost


def send_shared_job_email(job_post_id:int, emails: List[str]=None):
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
        return


def send_shared_job_chat(
    job_post_id:int,
    sender_id:int,
    talent_ids:List[UUID],
):
    user_ids = Talent.objects.filter(uid__in=talent_ids).only("user_id").values_list("user_id", flat=True)
    for user_id in user_ids:
        chat = Conversation.objects.filter(users__id=sender_id).filter(users__id=user_id).first()
        if not chat:
            chat = Conversation.objects.create()
            chat.users.add(user_id, sender_id)
            chat.save()
        if chat.message_set.filter(job_post_id=job_post_id).exists():
            continue
        Message.objects.create(conversation=chat, sender_id=sender_id, job_post_id=job_post_id)