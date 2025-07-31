from accounts.models import BusinessUser


def create_business_workflows(business_id):
    from settings.models import WorkFlowStage
    from jobs.enums import PhaseType
    business_user = BusinessUser.objects.filter(business_id=business_id).first()
    if not business_user:
        return
    phases = (PhaseType.NEW.value, PhaseType.HIRED.value, PhaseType.REJECTED.value)

    for phase in phases:
        workflow = WorkFlowStage.objects.filter(created_by=business_user, phase=phase).first()
        if not workflow:
            WorkFlowStage.objects.create(created_by=business_user, phase=phase, name=phase, phase_order=phases.index(phase))
    return







