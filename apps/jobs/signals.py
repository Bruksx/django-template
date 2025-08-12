from django.db.models.signals import pre_save, post_save
from django.dispatch import receiver
from django.utils import timezone

from jobs.models import TalentApplicationStageTimeline
from helpers.utils import to_utc
from jobs.enums import PhaseType, JobStatusType
from jobs.models import JobApplication, JobPost, JobPostMetrics, RequiredAttribute, Job, AvailableDay
from notification import notifications

from monkeypatches.q_cluster import async_task


@receiver(pre_save, sender=JobApplication)
def handle_stage_timeline_update(sender, instance, **kwargs):
    if instance.id:
         old_application = JobApplication.objects.filter(id=instance.id).first()
         if old_application.stage != instance.stage:
             instance.stage_date_updated = timezone.now()
             TalentApplicationStageTimeline.objects.filter(
                 application=instance, stage=old_application.stage
             ).update(exit_date=timezone.now())
             tf = TalentApplicationStageTimeline.objects.filter(
                 application=instance, stage=instance.stage
             ).first()
             if tf:
                 tf.exit_date = None
                 tf.save()
             else:
                 TalentApplicationStageTimeline.objects.create(stage=instance.stage, application=instance, job_role=instance.job_post.job.role)

@receiver(post_save, sender=JobApplication)
def handle_new_application(sender, instance,created,  **kwargs):
    if created:
        TalentApplicationStageTimeline.objects.create(stage=instance.stage, application=instance, job_role=instance.job_post.job.role)
        instance.stage_date_updated = timezone.now()
        instance.save()

@receiver(post_save, sender=JobPost)
def handle_new_job_post(sender, instance, created, **kwargs):
    if created:
        JobPostMetrics.objects.create(job_post=instance)

@receiver(post_save, sender=Job)
def handle_new_job(sender, instance, created, **kwargs):
    if created:
        async_task(instance.send_alerts)

@receiver(pre_save, sender=JobPost)
def handle_job_post_date(sender, instance, **kwargs):
    if instance.id:
        existing_instance = JobPost.objects.filter(id=instance.id).first()
        if not existing_instance:
            return
        if instance.status == JobStatusType.POSTED.value and existing_instance.status != JobStatusType.POSTED.value:
            instance.date_posted = timezone.now()
        elif instance.status != JobStatusType.DRAFT.value and existing_instance.status == JobStatusType.DRAFT.value:
            instance.date_posted = None
    else:
        if instance.status == JobStatusType.POSTED.value:
            instance.date_posted = timezone.now()
        elif instance.status != JobStatusType.DRAFT.value:
            instance.date_posted = None

@receiver(pre_save, sender=JobApplication)
def handle_new_application(sender, instance,  **kwargs):
    if not instance.id:
        instance.match = instance.applicant.job_match_score(instance.job_post)
        instance.recruiter = instance.job_post.recruiter


@receiver(pre_save, sender=JobPost)
def handle_job_post_recruiter(sender, instance, **kwargs):
    if not instance.pk:
        notifications.send_job_post_assignment_notification(
            job_post=instance)
    else:
        job_post = JobPost.objects.filter(id=instance.id).first()
        if job_post.recruiter != instance.recruiter:
            notifications.send_job_post_assignment_notification(
                job_post=instance, previous_recruiter=job_post.recruiter)

@receiver(post_save, sender=Job)
def handle_job_required_attributes(sender,  instance, created, **kwargs):
    if created:
        RequiredAttribute.objects.create(job=instance)


@receiver(pre_save, sender=AvailableDay)
def set_utc_times(sender, instance, *args, **kwargs):
    if instance.start_time:
        instance.utc_start_time = to_utc(instance.start_time, tzinfo=instance.job.availability_timezone.key)
    if instance.end_time:
        instance.utc_end_time = to_utc(instance.end_time, tzinfo=instance.job.availability_timezone.key)