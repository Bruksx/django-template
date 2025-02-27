from django.db.models.signals import pre_save, post_save
from django.dispatch import receiver
from django.utils import timezone

from jobs.enums import PhaseType, JobStatusType
from jobs.models import JobApplication, JobPost, JobPostMetrics
from notification import notifications


@receiver(pre_save, sender=JobApplication)
def handle_phase_timeline_update(sender, instance,  **kwargs):
    phases = [PhaseType.SCREENING.value, PhaseType.INTERVIEW.value,
              PhaseType.ONBOARDING.value, PhaseType.HIRED.value]
    attributes = ["posted_timeline", "screening_timeline", "interview_timeline", "onboarding_timeline"]
    today = timezone.now()
    if instance.id:
        application = JobApplication.objects.get(id=instance.id)
        if instance.stage and application.stage != instance.stage and instance.stage.phase != PhaseType.REJECTED.value:
            index = phases.index(instance.stage.phase)
            if application.stage is None:
                # if application is new and is being moved to next stage
                # bypass to current stage
                for i in range(index):
                    current_attribute = attributes[i]
                    setattr(instance, current_attribute, 0) # setting jumped timelines to 0
                current_attribute = attributes[index]
                setattr(instance, current_attribute, (today - instance.job_post.created_at).days)
                setattr(instance, "stage_date_updated", today)

            else:
                if application.stage.phase not in phases:
                    return
                # if an application is moved from a stage to another in a forward movement
                prev_index = phases.index(application.stage.phase)
                if prev_index < index:
                    for i in range(prev_index+1, index):
                        current_attribute = attributes[i]
                        setattr(instance, current_attribute, 0) # setting jumped timelines to 0
                    current_attribute = attributes[index]
                    setattr(instance, current_attribute, (today - instance.stage_date_updated).days)
                    setattr(instance, "stage_date_updated", today)
                else:
                    # if an application is moved from a stage to another in a backward movement
                    subtracted_days = 0
                    for i in (prev_index, index, -1):
                        current_attribute = attributes[i]
                        timeline = getattr(instance, current_attribute)
                        subtracted_days += timeline
                        setattr(instance, current_attribute, 0)
                    """ 
                        if current stage value doesnt change 
                        and stage_date_updated is updated to the stage_date_updated at 
                        the time initial stage movement happened
                    """
                    # stage_date_updated = application.stage_date_updated - timedelta(days=subtracted_days)
                    # setattr(instance, "stage_date_updated", stage_date_updated)

                    """
                        if current stage value changes, then stage_date_updated is not updated
                        then subtracted days will be added to the current stage value
                    """
                    current_attribute = attributes[index]
                    current_timeline = getattr(instance, current_attribute)
                    current_timeline += subtracted_days
                    setattr(instance, current_attribute, current_timeline)

        elif application.stage and not instance.stage:
            subtracted_days = 0
            index = phases.index(application.stage.phase)
            for i in (index, -1, -1):
                current_attribute = attributes[i]
                timeline = getattr(instance, current_attribute)
                subtracted_days += timeline
                setattr(instance, current_attribute, 0)
                instance.stage_date_updated - timezone.timedelta(days=subtracted_days)


@receiver(pre_save, sender=JobApplication)
def handle_stage_update(sender, instance,  **kwargs):
    if instance.id:
        application = JobApplication.objects.get(id=instance.id)
        if instance.stage and application.stage != instance.stage:
            if instance.stage.email_template:
                context = instance.get_email_context()
                instance.stage.email_template.send_email(context=context, to=[instance.applicant.user.email])


@receiver(pre_save, sender=JobApplication)
def handle_stage_timeline_update(sender, instance,  **kwargs):
    today = timezone.now()
    if instance.id:
        application = JobApplication.objects.get(id=instance.id)
        if instance.stage and application.stage != instance.stage:
            if application.stage is None:
                # if application is new and is being moved to next stage
                # bypass to current stage
                instance.stage.update_talent_stage_timeline(instance)
                previous_stages = instance.stage.previous_stages()
                for stage in previous_stages:
                    stage.update_talent_stage_timeline(instance)
            else:
                # if an application is moved from a stage to another in a forward movement
                prev_stage = application.stage
                if instance.stage.is_after(prev_stage):
                    previous_stages = instance.stage.previous_stages_after_stage(prev_stage)
                    if previous_stages:
                        for stage in previous_stages:
                            stage.update_talent_stage_timeline(instance, 0)
                    prev_stage.update_talent_stage_timeline(instance, (today - instance.stage_date_updated).days)
                    instance.stage.update_talent_stage_timeline(instance)
                    instance.stage_date_updated = today
                elif instance.stage.is_behind(prev_stage):
                    # if an application is moved from a stage to another in a backward movement
                    past_stages = instance.stage.next_stages_before_stage(prev_stage)
                    if past_stages:
                        accumulated_days = 0
                        for stage in past_stages:
                            stage_timeline = stage.get_talent_stage_timeline(instance)
                            accumulated_days += stage_timeline.timeline
                            stage_timeline.timeline = 0
                            stage_timeline.save()
                        """ 
                            if current stage value doesnt change 
                            and stage_date_updated is updated to the stage_date_updated at 
                            the time initial stage movement happened
                        """
                        # stage_date_updated = application.stage_date_updated - timedelta(days=subtracted_days)
                        # setattr(instance, "stage_date_updated", stage_date_updated)

                        """
                            if current stage value changes, then stage_date_updated is not updated
                            then subtracted days will be added to the current stage value
                        """
                        instance.stage.update_talent_stage_timeline(instance, accumulated_days)

        elif application.stage and not instance.stage:
            past_stages = application.stage.previous_stages()
            if past_stages:
                accumulated_days = 0
                for stage in past_stages:
                    stage_timeline = stage.get_talent_stage_timeline(instance)
                    accumulated_days += stage_timeline.timeline
                    stage_timeline.timeline = 0
                    stage_timeline.save()


@receiver(post_save, sender=JobPost)
def handle_job_post_metric(sender, instance, created, **kwargs):
    if created:
        JobPostMetrics.objects.create(job_post=instance)

@receiver(pre_save, sender=JobPost)
def handle_job_post_date(sender, instance, **kwargs):
    if instance.id:
        existing_instance = JobPost.objects.get(id=instance.id)
        if instance.status == JobStatusType.POSTED.value and existing_instance.status != JobStatusType.POSTED.value:
            instance.date_posted = timezone.now()
    else:
        if instance.status == JobStatusType.POSTED.value:
            instance.date_posted = timezone.now()

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

