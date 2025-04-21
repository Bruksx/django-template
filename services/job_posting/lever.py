from services.job_posting.services.lever import TriggerType, deploy_jobs


class LeverJobPostingService:

    @staticmethod
    def deploy(previous_object:None, current_object, trigger: TriggerType):
        return deploy_jobs(previous_object, current_object, trigger)


lever_job_posting_service = LeverJobPostingService()