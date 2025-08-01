from django.db.models.signals import pre_delete, post_save, pre_save
from django.dispatch import receiver
from helpers.utils import delete_s3_item

from settings.models import EmailTemplateAttachment, WorkFlowStage


@receiver(pre_delete, sender=EmailTemplateAttachment)
def handle_email_template_attachment_deletion(sender, instance, **kwargs):
    delete_s3_item(instance.file.url)
    instance.file.delete()

@receiver(post_save, sender=WorkFlowStage)
def assign_order_to_new_stage(sender, instance, created, **kwargs):
    if created:
        stage = WorkFlowStage.objects.filter(
            created_by__business=instance.created_by.business,
            phase=instance.phase
        ).exclude(id=instance.id).order_by("order").last()
        instance.order = stage.order + 1 if stage else 0
        instance.save()

