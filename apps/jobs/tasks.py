from concurrent.futures import ThreadPoolExecutor
from typing import List
from uuid import UUID

from monkeypatches.q_cluster import async_task

from accounts.models import Talent
from chats.models import Conversation, Message
from django.db import connection, close_old_connections, transaction
from jobs.models import JobPost, Job, JobInvite
from notification.notifications import send_job_application_notification, send_job_sharing_notification, \
    send_job_performance_notification

from jobs.enums import JobStatusType
from helpers.email.jobs import send_shared_job_email, send_invite_to_apply_email
from helpers.utils import chunk_queryset


def share_job_via_email(job_ids:List[UUID], emails: List[str]=None, language:str="en"):
    job_posts = JobPost.objects.filter(job__uid__in=job_ids).select_related('job').distinct("job_id")
    for job_post in job_posts:
        send_shared_job_email(job_post, emails, language)
        job_post.update_email_share()
    return

def send_shared_job_chat(
    job_ids:List[UUID],
    sender_id:int,
    talent_ids:List[UUID],
):
    talents = Talent.objects.select_related("user").filter(uid__in=talent_ids).only("user_id", "country_id", "user__fullname")
    for talent in talents:
        chat = Conversation.objects.filter(users__id=sender_id).filter(users__id=talent.user_id).first()
        if not chat:
            chat = Conversation.objects.create(locked=True)
            chat.users.add(talent.user_id, sender_id)
            chat.save()
        for job_uid in job_ids:
            job_post = JobPost.objects.select_related("job", "job__role").filter(job__uid=job_uid).first()
            if not job_post:
                continue
            if not chat.message_set.filter(job_post=job_post).exists():
                role = f"{job_post.job.role.name} role" if job_post.job.role else job_post.job.title
                text = f"Hi {talent.user.fullname}, I think that you would be a great match for this {role}! Click the button below to View Job and Apply."
                msg = Message.objects.create(conversation=chat, sender_id=sender_id, job_post=job_post, body=text)
                msg.handle_post_save(notify=True)



def invite_to_apply(sender_id:int, job_ids:List[UUID], talents: List[UUID], language="en"):
    async_task(send_shared_job_chat, job_ids, sender_id, talents)
    job_posts = JobPost.objects.filter(job__uid__in=job_ids).select_related('job').distinct("job_id")
    talents = Talent.objects.filter(uid__in=talents)
    for talent in talents:
        for job_post in job_posts:
            job = job_post.job
            if not JobInvite.objects.filter(job=job, talent=talent).exists():
                JobInvite.objects.create(job=job, talent=talent)
            send_invite_to_apply_email(job_post, talent.user.email, language)
    return



def job_application_notification_task():
    with transaction.atomic():
        job_posts = JobPost.objects.filter(status=JobStatusType.POSTED.value)
        with ThreadPoolExecutor(max_workers=20) as executor:
            for chunk in chunk_queryset(job_posts):
                executor.map(send_job_application_notification, chunk)
        connection.close()
        close_old_connections()
    return


def job_sharing_notification_task():
    with transaction.atomic():
        job_posts = JobPost.objects.filter(status=JobStatusType.POSTED.value)
        with ThreadPoolExecutor(max_workers=20) as executor:
            for chunk in chunk_queryset(job_posts):
                executor.map(send_job_sharing_notification, chunk)
        connection.close()
        close_old_connections()
    return



def job_performance_notification_task():
    with transaction.atomic():
        job_posts = JobPost.objects.filter(status=JobStatusType.POSTED.value)

        with ThreadPoolExecutor(max_workers=20) as executor:
            for chunk in chunk_queryset(job_posts):
                executor.map(send_job_performance_notification, chunk)

        connection.close()
        close_old_connections()
    return

def fetch_job_posts_from_lever():
    from services.job_posting.services.lever_job_download import import_lever_jobs
    import_lever_jobs()
