from datetime import timedelta, datetime, time

from django.utils import timezone

from jobs.models import JobPostMetrics
from .enums import EntityActionType, NotificationGroup
from .enums import EntityType, NotificationType
from .models import Notification, BusinessUserNotificationSettings


def send_new_chat_notification(chat):
    """
    args:
        chat: Chat
    send this notification when a new chat is created
    """
    if not chat:
        return

    notification = Notification.objects.create(
        title="New Chat Notification",
        description="You have a new chat",
        action=EntityActionType.NEW.value,
        notification_type=NotificationType.USER.value,
        entity=EntityType.CHAT.value,
        entity_uid=chat.uid,
        entity_str=str(chat),
    )
    notification.recipient_users.add(*chat.users.all())
    notification.save()
    notification.notify()

def send_new_chat_message_notification(message):
    """
    args:
        chat: Chat
    send this notification when a new chat is created
    """
    if not message:
        return

    notification = Notification.objects.create(
        title=f"New chat message from {message.sender.fullname}",
        description=str(message),
        action=EntityActionType.NEW.value,
        notification_type=NotificationType.USER.value,
        entity=EntityType.CHAT.value,
        entity_uid=message.conversation.uid,
        entity_str=str(message.conversation),
    )
    recipient = message.conversation.get_recipient(message.sender)
    notification.recipient_users.add(recipient)
    notification.save()
    notification.notify()

def send_job_alert_notification(job, user_ids):
    from accounts.models import User
    notification = Notification.objects.create(
        title=job.title,
        description=job.about or "",
        action=EntityActionType.NEW.value,
        notification_type=NotificationType.USER.value,
        entity=EntityType.JOB.value,
        entity_uid=job.uid,
        entity_str=str(job),
    )
    notification.recipient_users.add(*User.objects.filter(id__in=user_ids))
    notification.save()
    notification.notify()


def send_job_post_application_notification(job_post, start_date, end_date):
    job_title = job_post.job.title
    application_count = job_post.jobapplication_set.filter(created_at__range=(start_date, end_date)).count()
    if application_count == 0:
        return
    notification = Notification(
        title="New Job Applications",
        description=f"You have {application_count} new applications for {job_title}",
        action=EntityActionType.NEW.value,
        notification_type=NotificationType.APPLICANTS.value,
        entity=EntityType.JOB_POST.value,
        entity_uid=job_post.uid,
        entity_str=str(job_post),
        recipient_groups=[NotificationGroup.BUSINESS_USERS.value],
        business=job_post.recruiter.business
    )
    notification.save()
    notification.notify()


def send_job_application_notification(job_post):
    """
    Trigger Timing: Daily at 5am, 10am, 4pm
    Example Notification:
    "You have 15 new applications for [Job_Title].

    """

    now = timezone.now()
    yesterday = timezone.now() - timedelta(days=1)

    if now.hour  == 5:
        start_date = datetime.combine(yesterday.date(), time(hour=16, minute=0, second=0), tzinfo=yesterday.tzinfo)
        end_date = datetime.combine(now.date(), time(hour=5, minute=0, second=0), tzinfo=now.tzinfo)

    elif now.hour == 10:
        start_date = datetime.combine(now.date(), time(hour=5, minute=0, second=0), tzinfo=now.tzinfo)
        end_date = datetime.combine(now.date(), time(hour=10, minute=0, second=0), tzinfo=now.tzinfo)

    elif now.hour == 16:
        start_date = datetime.combine(now.date(), time(hour=10, minute=0, second=0), tzinfo=now.tzinfo)
        end_date = datetime.combine(now.date(), time(hour=16, minute=0, second=0), tzinfo=now.tzinfo)

    else:
        return

    send_job_post_application_notification(job_post, start_date, end_date)





def send_talent_job_matching_notification(talent, job_post):
    """
    args:
        talent: Talent
        job_post: JobPost
    send this notification when a new job_post is viewed by a talent

    """
    "High match alert! [Candidate_Name]'s profile matches the requirements for [Job_Title]."
    """
    """

    today = timezone.now()
    match_score = talent.job_match_score(job_post)

    if match_score < 80:
        return

    # this notification is only sent once a day
    if Notification.objects.filter(
        notification_type=NotificationType.MATCHING.value,
        entity=EntityType.JOB_POST.value,
        entity_uid=job_post.uid,
        description__icontains=talent.user.fullname,
         created_at__year=today.year,
         created_at__month=today.month,
         created_at__day=today.day).exists():
        return

    notification = Notification(
        title="Job Matching",
        description=f"High match alert! {talent.user.fullname}'s profile matches with the requirements for {job_post.job.title}%",
        notification_type=NotificationType.MATCHING.value,
        entity=EntityType.JOB_POST.value,
        entity_uid=job_post.uid,
        entity_str=str(job_post),
        recipient_groups=[NotificationGroup.BUSINESS_USERS.value],
        business=job_post.recruiter.business
    )
    notification.save()
    notification.notify()

def send_talents_job_matching_notification(talent_count, job_post):
    if talent_count == 0:
        return
    notification = Notification(
        title="Job Matching",
        description=f"High match alert! {talent_count} talents' profile match with the requirements for {job_post.job.title}",
        notification_type=NotificationType.MATCHING.value,
        entity=EntityType.JOB_POST.value,
        entity_uid=job_post.uid,
        entity_str=str(job_post),
        recipient_groups=[NotificationGroup.BUSINESS_USERS.value],
        business=job_post.recruiter.business)
    notification.save()
    notification.notify()


def send_job_sharing_notification(job_post):
    """
    Trigger Timing: Batch Daily at 4pm
    Example Notification:
    "Your job post for [Job_Title] was shared x times today"

    """

    now = timezone.now()
    yesterday = now - timedelta(days=1)
    if not hasattr(job_post, "jobpostmetrics"):
        JobPostMetrics.objects.create(job_post=job_post)

    metric = job_post.jobpostmetrics

    email_shares = metric.daily_email_shares
    metric.reset_daily_email_shares()

    chat_shares = job_post.message_set.filter(
        created_at__range=(yesterday, now)
    ).count()
    total_shares = email_shares + chat_shares
    if total_shares == 0:
        return
    job_title = job_post.job.title

    notification = Notification(
        title="Job Shared",
        description=f"Your job post for {job_title} was shared {total_shares} times today",
        notification_type=NotificationType.SHARING.value,
        entity=EntityType.JOB_POST.value,
        entity_uid=job_post.uid,
        entity_str=job_post.job.title,
        recipient_groups=[NotificationGroup.BUSINESS_USERS.value],
        business=job_post.recruiter.business
    )
    notification.save()
    notification.notify()


def send_job_performance_notification(job_post):
    now = timezone.now()
    last_week = now - timedelta(days=7)

    if not hasattr(job_post, "jobpostmetrics"):
        JobPostMetrics.objects.create(job_post=job_post)

    metric = job_post.jobpostmetrics
    views = metric.weekly_views
    metric.reset_weekly_views()
    # may change
    applications = job_post.jobapplication_set.filter(
        created_at__range=(last_week, now)
    ).count()
    job_title = job_post.job.title

    matches = job_post.get_talents().count()

    if views == applications == matches == 0:
        return

    notification = Notification.objects.create(
        title="Job Performance Weekly Update",
        description=f"Weekly Update: [{job_title}] - {views} views, {applications} applications, {matches} matches.",
        notification_type=NotificationType.PERFORMANCE.value,
        entity=EntityType.JOB_POST.value,
        entity_uid=job_post.uid,
        entity_str=job_post.job.title,
        recipient_groups=[NotificationGroup.BUSINESS_USERS.value],
        business=job_post.recruiter.business
    )
    notification.save()
    notification.notify()


def send_business_user_notification(business_user, action: EntityActionType, action_str: str=""):
    """
    args:
        business_user: BusinessUser
        action: EntityActionType
        action_str: str

    send this notification on updates regarding a business user
    """
    if not business_user or not action:
        return

    description_mapping =  {
        EntityActionType.NEW.value: f"{business_user.user.fullname} has been added to your company profile",
        EntityActionType.UPDATE.value: f"{business_user.user.fullname} {action_str}",
        EntityActionType.DELETE.value: f"{business_user.user.fullname} has deleted their account",
    }
    notification = Notification(
        title="New Business User",
        description=description_mapping[action],
        action=action.value,
        notification_type=NotificationType.USER.value,
        entity=EntityType.BUSINESS_USER.value,
        entity_uid=business_user.uid,
        entity_str=business_user.business.name,
        recipient_groups=[NotificationGroup.BUSINESS_USERS.value],
        business=business_user.business
    )
    notification.save()
    notification.notify()


def send_job_post_assignment_notification(job_post, previous_recruiter=None):
    """
    args:
        job_post: JobPost
        previous_recruiter: Optional[BusinessUser]

    send this notification when a job_post is assigned
    """

    if previous_recruiter and BusinessUserNotificationSettings.should_send_notification(
            previous_recruiter.user, NotificationType.ASSIGNMENT.value
    ):
        notification = Notification.objects.create(
            title="Job Re-Assignment",
            description=f"{job_post.job.title} has been re-assigned from you",
            notification_type=NotificationType.ASSIGNMENT.value,
            entity=EntityType.JOB_POST.value,
            entity_uid=job_post.uid,
            entity_str=job_post.job.title,
            business=job_post.recruiter.business
        )
        notification.recipient_users.add(previous_recruiter.user)
        notification.save()
        notification.notify()
    if BusinessUserNotificationSettings.should_send_notification(
        job_post.recruiter.user, NotificationType.ASSIGNMENT.value
    ):
        notification = Notification.objects.create(
            title="Job Assignment",
            description=f"{job_post.job.title} has been assigned to you",
            notification_type=NotificationType.ASSIGNMENT.value,
            entity=EntityType.JOB_POST.value,
            entity_uid=job_post.uid,
            entity_str=job_post.job.title,
            business=job_post.recruiter.business
        )
        notification.recipient_users.add(job_post.recruiter.user)
        notification.save()
        notification.notify()



