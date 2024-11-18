from datetime import timedelta

from django.utils import timezone

from .enums import EntityActionType, NotificationGroup
from .enums import EntityType, NotificationType
from .models import Notification, BusinessUserNotificationSettings


def send_new_chat_notification(chat):
    """
    args:
        chat: Chat
    send this notification when a new chat is created
    """
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


def send_job_application_notification(job_application):
    """
    args:
        job_application: JobApplication
    send this notification when a new job application is created
    """
    talent_name = job_application.applicant.user.fullname
    job_title = job_application.job_post.job.title
    notification = Notification.objects.create(
        title="New Job Application",
        description=f"{talent_name} applied for {job_title}",
        action=EntityActionType.NEW.value,
        notification_type=NotificationType.APPLICANTS.value,
        entity=EntityType.JOB_APPLICATION.value,
        entity_uid=job_application.uid,
        entity_str=str(job_application),
        recipient_groups=[NotificationGroup.BUSINESS_USERS.value],
        business=job_application.job_post.recruiter.business
    )
    notification.save()
    notification.notify()


def send_talent_job_matching_notification(talent, job_post):
    """
    args:
        talent: Talent
        job_post: JobPost
    send this notification when a new job_post is viewed by a talent
    """
    today = timezone.now()
    match_score = talent.job_match_score(job_post)

    if match_score < 50:
        return

    # this notification is only sent once a day
    if Notification.objects.filter(
        notification_type=NotificationType.MATCHING.value,
        entity=EntityType.JOB_POST.value,
        entity_uid=job_post.uid
    ).filter(description__icontains=talent.user.fullname,
             created_at__year=today.year,
             created_at__month=today.month,
             created_at__day=today.day).exist():
        return

    notification = Notification.objects.create(
        title="Job Matching",
        description=f"{talent.user.fullname} matched with {job_post.job.title} with a score of {match_score}%",
        notification_type=NotificationType.MATCHING.value,
        entity=EntityType.JOB_POST.value,
        entity_uid=job_post.uid,
        entity_str=str(job_post),
        recipient_groups=[NotificationGroup.BUSINESS_USERS.value],
        business=job_post.recruiter.business
    )
    notification.save()
    notification.notify()


def send_job_sharing_notification(job_post, sender, talent):
    """
    args:
        job_post: JobPost
        sender: User
        talent: User

    send this notification when a job_post is shared
    we need to send this notification to the recipient and the business connected
    to the job being shared
    """
    notification = Notification.objects.create(
        title="Invitation to Apply",
        description=f"{sender.fullname} shared a job with you",
        entity=EntityType.JOB_POST.value,
        entity_uid=job_post.uid,
        entity_str=job_post.job.title,
    )
    notification.recipient_users.add(talent)
    notification.save()
    notification.notify()

    notification = Notification.objects.create(
        title="Job Shared",
        description=f"{sender.fullname} shared a job with {talent.fullname}",
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
    """ Todo
    yet to be determined

    """
    job_performance = 0

    notification = Notification.objects.create(
        title="Job Performance",
        description=f"{job_post.job.title} has a performance score of {job_performance}% ",
        notification_type=NotificationType.PERFORMANCE.value,
        entity=EntityType.JOB_POST.value,
        entity_uid=job_post.uid,
        entity_str=job_post.job.title,
        recipient_groups=[NotificationGroup.BUSINESS_USERS.value],
        business=job_post.recruiter.business
    )
    notification.save()
    notification.notify()


def send_business_user_notification(business_user, action: EntityActionType, action_str: str):
    """
    args:
        business_user: BusinessUser
        action: EntityActionType
        action_str: str

    send this notification on updates regarding a business user
    """
    description_mapping =  {
        EntityActionType.NEW: f"{business_user.user.fullname} has joined your business",
        EntityActionType.UPDATE: f"{business_user.user.fullname} {action_str}",
        EntityActionType.DELETE: f"{business_user.user.fullname} has deleted their account",
    }
    notification = Notification.objects.create(
        title="New Business User",
        description=description_mapping[action],
        action=action,
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
            previous_recruiter, NotificationType.ASSIGNMENT.value
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
        job_post.recruiter, NotificationType.ASSIGNMENT.value
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



