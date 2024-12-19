from concurrent.futures import ThreadPoolExecutor
from typing import List
from uuid import UUID

from accounts.models import Talent
from chats.models import Conversation, Message
from django.db import connection, close_old_connections
from jobs.models import JobPost
from notification.notifications import send_job_application_notification, send_job_sharing_notification, \
    send_job_performance_notification

from apps.jobs.enums import JobStatusType
from helpers.email.jobs import send_shared_job_email
from helpers.utils import chunk_queryset


def share_job_via_email(job_post_ids:List[UUID], emails: List[str]=None, language:str="en"):
    job_posts = JobPost.objects.filter(uid__in=job_post_ids).select_related('job')
    for job_post in job_posts:
        send_shared_job_email(job_post, emails, language)
        job_post.update_email_share()
    return


def send_shared_job_chat(
    job_post_ids:List[UUID],
    sender_id:int,
    talent_ids:List[UUID],
):
    user_ids = Talent.objects.filter(uid__in=talent_ids).only("user_id").values_list("user_id", flat=True)
    job_post_ids = JobPost.objects.filter(uid__in=job_post_ids).only("id").values_list("id", flat=True)
    for user_id in user_ids:
        chat = Conversation.objects.filter(users__id=sender_id).filter(users__id=user_id).first()
        if not chat:
            chat = Conversation.objects.create()
            chat.users.add(user_id, sender_id)
            chat.save()
        for job_post_id in job_post_ids:
            if chat.message_set.filter(job_post_id=job_post_id).exists():
                continue
            Message.objects.create(conversation=chat, sender_id=sender_id, job_post_id=job_post_id)


def job_application_notification_task():
    job_posts = JobPost.objects.filter(status=JobStatusType.POSTED.value)
    with ThreadPoolExecutor(max_workers=20) as executor:
        for chunk in chunk_queryset(job_posts):
            executor.map(send_job_application_notification, chunk)
    connection.close()
    close_old_connections()
    return


def job_sharing_notification_task():
    job_posts = JobPost.objects.filter(status=JobStatusType.POSTED.value)
    with ThreadPoolExecutor(max_workers=20) as executor:
        for chunk in chunk_queryset(job_posts):
            executor.map(send_job_sharing_notification, chunk)
    connection.close()
    close_old_connections()
    return



def job_performance_notification_task():
    job_posts = JobPost.objects.filter(status=JobStatusType.POSTED.value)

    with ThreadPoolExecutor(max_workers=20) as executor:
        for chunk in chunk_queryset(job_posts):
            executor.map(send_job_performance_notification, chunk)

    connection.close()
    close_old_connections()
    return
