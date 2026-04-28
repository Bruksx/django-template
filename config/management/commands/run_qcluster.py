import logging

from django.core.management.base import BaseCommand
from django_q.management.commands.qcluster import Command as QClusterCommand

logger = logging.getLogger(__name__)

class Command(BaseCommand):
    help = 'Runs the Django Q cluster with custom behavior'

    def handle(self, *args, **kwargs):
        from monkeypatches.q_cluster import schedule_cron_tasks
        from apps.jobs.scheduler import tasks as job_tasks
        from apps.accounts.scheduler import tasks as account_tasks
        from apps.notification.scheduler import tasks as notification_tasks
        from apps.core.scheduler import tasks as core_tasks
        # you may add other cron tasks here
        tasks = (*account_tasks, *job_tasks, *notification_tasks, *core_tasks)

        schedule_cron_tasks(tasks)

        # Call the original qcluster command
        original_qcluster = QClusterCommand()
        original_qcluster.handle(*args, **kwargs)

