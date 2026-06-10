from django.db.models.signals import post_save, pre_save
from django.dispatch import receiver

from accounts.enums import UserType
from accounts.models import Experience, Talent, BusinessUser, TalentAvailableDay
from accounts.services.business import create_business_workflows
from helpers.utils import to_utc
from monkeypatches.q_cluster import async_task


@receiver(post_save, sender=Experience)
def update_talent_years_of_experience(sender, instance, created, **kwargs):
    years, month = instance.talent.calculate_years_of_experience()
    avg_tenure = instance.talent.calculate_avg_experience_tenure()
    instance.talent.years_of_experience = years
    instance.talent.months_of_experience = month
    instance.talent.average_experience_tenure = avg_tenure
    instance.talent.save(update_fields=["years_of_experience", "months_of_experience", "average_experience_tenure"])


@receiver(post_save, sender=Talent)
def update_talent_user_type(sender, instance, created, **kwargs):
    if created:
        instance.user.type = UserType.TALENT.value
        instance.user.save()


@receiver(post_save, sender=BusinessUser)
def update_business_user_type(sender, instance, created, **kwargs):
    if created:
        instance.user.type = UserType.BUSINESS.value
        instance.user.save()
        if BusinessUser.objects.filter(business=instance.business).count() == 1:
            async_task(create_business_workflows, instance.business.id)


@receiver(post_save, sender=BusinessUser)
def create_notification_setting(sender, instance, created, **kwargs):
    from notification.models import BusinessUserNotificationSettings #noqa
    if created:
        BusinessUserNotificationSettings.objects.create(business_user=instance)



@receiver(pre_save, sender=TalentAvailableDay)
def set_utc_times(sender, instance, *args, **kwargs):
    if instance.start_time:
        instance.utc_start_time = to_utc(instance.start_time, tzinfo=instance.talent.availability_timezone.key)
    if instance.end_time:
        instance.utc_end_time = to_utc(instance.end_time, tzinfo=instance.talent.availability_timezone.key)