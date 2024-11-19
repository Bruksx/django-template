from django.db.models.signals import pre_delete
from django.dispatch import receiver

from settings.models import EmailTemplateAttachment

from helpers.utils import delete_s3_item


@receiver(pre_delete, sender=EmailTemplateAttachment)
def handle_email_template_attachment_deletion(sender, instance, **kwargs):
    delete_s3_item(instance.file.name)
    instance.file.delete()
