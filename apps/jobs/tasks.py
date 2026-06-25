from concurrent.futures import ThreadPoolExecutor, as_completed
from typing import List
from uuid import UUID

from django.db import connection, close_old_connections, transaction
from django.db.models import Count

from accounts.models import Talent
from chats.models import Conversation, Message
from helpers.email.jobs import send_shared_job_email, send_invite_to_apply_email
from helpers.utils import chunk_queryset
from jobs.enums import JobStatusType
from jobs.models import JobPost, JobInvite, JobPostTag
from monkeypatches.q_cluster import async_task
from notification.notifications import send_job_application_notification, send_job_sharing_notification, \
    send_job_performance_notification


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
    """Scheduled task to send job application notifications (5am, 10am, 4pm)"""

    job_posts = JobPost.objects.filter(
        status=JobStatusType.POSTED.value
    ).select_related('job', 'job__created_by')  # optimize queries

    if not job_posts.exists():
        return

    # Process in chunks to avoid memory issues
    def process_job_post(job_post):
        try:
            # Each notification runs in its own transaction
            with transaction.atomic():
                send_job_application_notification(job_post)
        except Exception as e:
            # Log error but don't stop the whole task
            print(f"Error sending application notification for job {job_post.uid}: {e}")
            # You can add proper logging here (logger.error(...))

    # Use ThreadPool for parallel processing
    with ThreadPoolExecutor(max_workers=20) as executor:
        futures = []

        for chunk in chunk_queryset(job_posts):  # adjust chunk_size as needed
            for job_post in chunk:
                future = executor.submit(process_job_post, job_post)
                futures.append(future)

        # Wait for all tasks to complete and handle exceptions
        for future in as_completed(futures):
            try:
                future.result()
            except Exception as e:
                print(f"Thread error: {e}")

    # Clean up database connections after using threads
    close_old_connections()
    connection.close()

    return "Job application notifications task completed"


def job_sharing_notification_task():
    """
    Scheduled task (Daily at 4 PM)
    Sends job sharing summary notifications to business users.
    """
    job_posts = JobPost.objects.filter(
        status=JobStatusType.POSTED.value
    ).select_related(
        'job',
        'job__created_by',
        'jobpostmetrics'
    ).prefetch_related('message_set')  # optimize for send_job_sharing_notification

    if not job_posts.exists():
        return "No active job posts"

    def process_job_post(job_post):
        """Process single job post safely"""
        try:
            with transaction.atomic():
                send_job_sharing_notification(job_post)
        except Exception as e:
            # TODO: Replace with proper logging (e.g. structlog / logging)
            print(f"Error sending sharing notification for job {job_post.uid}: {e}")
            # logger.error(...)

    # Parallel processing with better control
    with ThreadPoolExecutor(max_workers=20) as executor:
        futures = [
            executor.submit(process_job_post, job_post)
            for chunk in chunk_queryset(job_posts)
            for job_post in chunk
        ]

        # Wait and handle exceptions
        for future in as_completed(futures):
            try:
                future.result()
            except Exception as e:
                print(f"Thread execution error: {e}")

    # Clean up connections after using threads
    close_old_connections()
    if connection:
        connection.close()

    return "Job sharing notification task completed"

def job_performance_notification_task():
    """
    Weekly job performance notification task.
    """
    job_posts = JobPost.objects.filter(
        status=JobStatusType.POSTED.value
    ).select_related('job', 'job__created_by', 'jobpostmetrics')

    success_count = 0
    error_count = 0

    for job_post in job_posts.iterator():   # memory-efficient
        try:
            with transaction.atomic():
                send_job_performance_notification(job_post)
            success_count += 1
        except Exception as e:
            error_count += 1
            print(f"Failed for job {job_post.uid}: {e}")

    close_old_connections()

    return f"Performance task completed. Success: {success_count}, Errors: {error_count}"


# def fetch_job_posts_from_lever():
#     from services.job_posting.services.lever_job_download import import_lever_jobs
#     import_lever_jobs()


def delete_tags_with_no_job_posts():
    unused = (
        JobPostTag.objects
        .annotate(job_count=Count("job_posts"))
        .filter(job_count=0)
    )
    if unused.exists():
        unused.delete()
