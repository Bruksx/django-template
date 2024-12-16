from django.core.management.base import BaseCommand
from django_q.management.commands.qcluster import Command as QClusterCommand
import logging

logger = logging.getLogger(__name__)

class Command(BaseCommand):
    help = 'Runs the Django Q cluster with custom behavior'

    def handle(self, *args, **kwargs):
        from monkeypatches.q_cluster import schedule_cron_tasks
        from apps.jobs import scheduler
        # you may add other cron tasks here
        tasks = (*scheduler.tasks,)

        schedule_cron_tasks(tasks)

        # Call the original qcluster command
        original_qcluster = QClusterCommand()
        original_qcluster.handle(*args, **kwargs)

