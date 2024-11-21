from django.db.models.signals import pre_delete, post_save
from django.dispatch import receiver

from jobs.enums import PhaseType
from settings.models import EmailTemplateAttachment

from helpers.utils import delete_s3_item

from settings.schemas import WorkFlowStageSchema


@receiver(pre_delete, sender=EmailTemplateAttachment)
def handle_email_template_attachment_deletion(sender, instance, **kwargs):
    delete_s3_item(instance.file.name)
    instance.file.delete()

@receiver(post_save, sender=WorkFlowStageSchema)
def assign_order_to_new_stage(sender, instance, created, **kwargs):
    if created:
        stage = WorkFlowStageSchema.objects.filter(
            created_by__business=instance.created_by.business,
            phase=instance.phase
        ).only("id", "order").order_by("-order").first()
        if stage:
            if stage.id != instance.id:
                order = stage.order + 1
                instance.order = order
        instance.phase_order = PhaseType.values().index(instance.phase)
        instance.save()



