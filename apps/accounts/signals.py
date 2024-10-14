from django.db.models.signals import post_save
from django.dispatch import receiver

from accounts.models import Experience


@receiver(post_save, sender=Experience)
def update_talent_years_of_experience(sender, instance, created, **kwargs):
    new_talent_years_of_experience = instance.talent.get_years_of_experience()
    instance.talent.years_of_experience = new_talent_years_of_experience
    instance.talent.save()
