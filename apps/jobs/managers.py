from accounts.models import Department, Role,  Country, User
from core.models import BaseManager


class JobManager(BaseManager):
    def create_job(self, *, business_user, data):
        from .models import (
            EmploymentType, AvailableDay, Language, BusinessModel, JobLevel, JobPost, ScreeningQuestion, QuestionOption,
        )
        Job = self.model
        data_dict = data.dict()
        first_language = Language.objects.filter(uid=data.first_language_uid).first()
        employment_type = EmploymentType.objects.filter(uid=data.employment_type_uid).first()
        department = Department.objects.filter(uid=data.department_uid).first()
        role = Role.objects.filter(uid=data.role_uid).first()
        job_level = JobLevel.objects.filter(uid=data.job_level_uid).first()
        recruiter = User.objects.filter(uid=data.recruiter_uid).first()

        to_be_deleted = [
            "employment_type_uid", "first_language_uid", "role_uid", "job_level_uid","additional_languages", "skills", 
            "availability", "technological_requirements", "job_posts", "recruiter_uid", "same_recruiter", "screening_questions", 
            "department_uid", "work_structure", "lunch_break",
        ]

        for attr in to_be_deleted:
            del data_dict[attr]

        job = Job(**data_dict)
        job.created_by = business_user
        job.business = business_user.business
        job.first_language = first_language
        job.department = department
        job.employment_type = employment_type
        job.role = role
        job.job_level = job_level
        job.recruiter = recruiter
        job.save()

        for i in data.availability:
            available_day = AvailableDay(job=job, **i.dict())
            available_day.save()
        for i in data.job_posts:
            country = Country.objects.filter(code=i.country_code).first()
            post = JobPost(
                job=job,
                country=country,
                province=i.province,
                postal_code=i.postal_code,
            )
            if data.same_recruiter:
                post.recruiter = recruiter
            post.save()
        for i in data.screening_questions:
            question = ScreeningQuestion(
                job=job,
                type=i.type.value,
                text=i.text,
                is_knockout=i.is_knockout,
            )
            question.save()
            for option in i.options:
                question_option = QuestionOption(
                    question=question,
                    is_accepted=option.is_accepted,
                    text=option.text,
                )
                question_option.save()
        job.skills.set(data.skills)
        return job