import os

import django

os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'config.settings')
django.setup()
from jobs.enums import PhaseType
from settings.models import WorkFlowStage


for workflow in WorkFlowStage.objects.iterator():
    index = PhaseType.get_index(workflow.phase)
    phase = PhaseType.from_index(index)
    if not phase:
        continue
    workflow.phase = phase.value
    workflow.phase_order = index
    workflow.save()

print("updated jobs with recent business models")


