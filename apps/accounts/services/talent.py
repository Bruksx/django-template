import json
from datetime import timedelta, date
from types import NoneType

from django.db import transaction
from django.db.models import Window, F
from django.db.models.functions import RowNumber
from django.utils import timezone
from django_q.models import Schedule
from ninja.errors import HttpError

from accounts.enums import UserType
from accounts.models import User, Talent, Experience, Education, TalentAvailableDay
from helpers.email.auth import send_admin_created_account_email
from jobs.services import get_talent_job_recommendations
from monkeypatches.q_cluster import async_task


@transaction.atomic
def update_talent_profile_service(talent: Talent, data: dict) -> Talent:
    """
    Reusable service function to update talent profile
    Used by both talent self-service and admin endpoints
    """

    if "gender" in data:
        data["gender"] = data["gender"].value if type(data["gender"]) is not str else data["gender"]

    if "work_models" in data:
        wm_func = lambda x: x.value if type(x) is not str else x
        if data["work_models"] is not None:
            data["work_models"] = list(map(wm_func, data["work_models"]))

    if "preferred_communication" in data:
        data["preferred_communication"] = data["preferred_communication"].value if type(data["preferred_communication"])  not in (str, NoneType) else data["preferred_communication"]
    
    if "notice_period_type" in data:
        data["notice_period_type"] = data["notice_period_type"].value if type(data["notice_period_type"])  not in (str, NoneType) else data["notice_period_type"]
    
    if "notice_period" in data:
        data["notice_period"] = data["notice_period"] if type(data["notice_period"])  not in (str, NoneType) else int(data["notice_period"]) if str(data["notice_period"]).isdigit() else None

    user = talent.user
    user_data = dict()
    
    # Handle user fields
    if "first_name" in data:
        user_data["first_name"] = data.pop("first_name", None)
    if "last_name" in data:
        user_data["last_name"] = data.pop("last_name", None)
    if "gender" in data:
        user_data["gender"] = data.pop("gender", None)
    if "phone_number" in data:
        user_data["phone_number"] = data.pop("phone_number")
    if "phone_code" in data:
        user_data["phone_code"] = data.pop("phone_code")

    # Handle photo (base64 conversion - this would need the helper function)
    if "photo" in data:
        # This would need the convert_base64_to_image_file function
        # data["photo"] = convert_base64_to_image_file(data["photo"])
        pass
    if not data.get("visible"):
        data.pop("visible", None)

    # Handle many-to-many relationships
    if "skills" in data:
        if data["skills"]:
            talent.skills.set(data.pop("skills"))
        else:
            data.pop("skills", None)
            talent.skills.clear()
    
    if "business_models" in data:
        if data["business_models"]:
            talent.business_models.set(data.pop("business_models"))
        else:
            data.pop("business_models", None)
            talent.business_models.clear()

    # Handle experience history
    if "experience_history" in data and data["experience_history"]:
        uids = list()
        for experience in data.pop("experience_history"):
            experience_uid = experience.pop("uid", None)
            currently_works = experience.get("currently_works_here", False)
            start_date = experience.get("start_date", None)
            end_date = experience.get("end_date", None)
            
            if experience.get("salary_type"):
                experience["salary_type"] = experience["salary_type"].value if type(experience["salary_type"]) is not str else experience["salary_type"]

            if experience.get("salary_bonus_type"):
                experience["salary_bonus_type"] = experience["salary_bonus_type"].value if type(experience["salary_bonus_type"]) is not str else experience["salary_bonus_type"]

            if not start_date:
                raise HttpError(400, "Experience start date is required")
            
            if currently_works is True:
                experience["end_date"] = None
            else:
                if not end_date:
                    raise HttpError(400, "Experience end date is required if not currently working here")
                if end_date < start_date:
                    raise HttpError(400, "Experience end date cannot be before start date")
                if end_date > timezone.now().date():
                    raise HttpError(400, "Experience end date cannot be in the future")

            if experience_uid:
                talent.experience_set.filter(uid=experience_uid).update(**experience)
                uids.append(experience_uid)
            else:
                experience = Experience.objects.create(**experience, talent=talent)
                uids.append(experience.uid)
        talent.experience_set.exclude(uid__in=uids).hard_delete()

    # Handle education history
    if "education_history" in data and data["education_history"]:
        uids = list()
        for education in data.pop("education_history"):
            edu_uid = education.pop("uid", None)
            if edu_uid:
                talent.education_set.filter(uid=edu_uid).update(**education)
                uids.append(edu_uid)
            else:
                education = Education.objects.create(**education, talent=talent)
                uids.append(education.uid)
        talent.education_set.exclude(uid__in=uids).hard_delete()

    # Handle additional languages
    if "additional_languages" in data:
        additional_languages = data.pop("additional_languages", list())
        if additional_languages:
            talent.additional_languages.set(additional_languages)
        else:
            talent.additional_languages.clear()



    # Handle employment types
    if "employment_types" in data:
        employment_types = data.pop("employment_types", list())
        if employment_types:
            talent.employment_types.set(employment_types)
        else:
            talent.employment_types.clear()

    # Handle availability
    if "availability" in data and data["availability"]:
        for available_day in data.pop("availability"):
            available_day["day"] = available_day["day"].value
            uid = available_day.pop("uid", None)
            active = available_day.pop("active", True)
            if uid and not active:
                talent.talentavailableday_set.filter(uid=uid).delete()
            elif uid and active:
                talent.talentavailableday_set.filter(uid=uid).update(**available_day)
            elif not uid:
                day = available_day['day']
                if not talent.talentavailableday_set.filter(day=day).exists():
                    TalentAvailableDay.objects.create(**available_day, talent=talent)

    # Clean up already handled fields
    data.pop("skills", None)
    data.pop("business_models", None)
    
    # Update user and talent
    if user_data:
        user.update(**user_data)
    
    return talent.update(**data)


@transaction.atomic
def create_talent_profile_service(data: dict) -> Talent:
    # Extract user fields
    first_name = data.pop("first_name", None)
    last_name = data.pop("last_name", None)
    email = data.pop("email", None)
    phone_code = data.pop("phone_code", None)
    phone_number = data.pop("phone_number", None)
    gender = data.pop("gender", None)

    # Extract talent fields
    country_uid = data.pop("country", None)
    state_uid = data.pop("state", None)
    role_uid = data.pop("role", None)
    employment_type_uids = data.pop("employment_types", [])
    native_language_uid = data.pop("native_language", None)
    additional_language_uids = data.pop("additional_languages", [])
    skill_uids = data.pop("skills", [])
    business_model_uids = data.pop("business_models", [])
    education_history = data.pop("education_history", [])
    experience_history = data.pop("experience_history", [])
    availability = data.pop("availability", [])

    # Validate required fields
    if not email:
        raise HttpError(400, "Email is required")
    if not first_name:
        raise HttpError(400, "First name is required")
    if not last_name:
        raise HttpError(400, "Last name is required")

    # Check email uniqueness — Fix 4: block ALL existing active users, not just talents
    existing_user = User.objects.filter(email__iexact=email).first()
    if existing_user:
        if existing_user.deleted_at is not None or not Talent.objects.filter(user=existing_user).exists():
            # deleted user OR active user without talent profile — either way, block reuse
            raise HttpError(400, "This email is not available")
        raise HttpError(400, "This email is not available")

    # Fix 1: use the already-popped `gender` variable, not data["gender"]
    if gender:
        gender = gender.value if not isinstance(gender, str) else gender

    if "work_models" in data and data["work_models"] is not None:
        data["work_models"] = [
            x.value if not isinstance(x, str) else x
            for x in data["work_models"]
        ]

    if "preferred_communication" in data and data["preferred_communication"]:
        pc = data["preferred_communication"]
        data["preferred_communication"] = pc.value if not isinstance(pc, str) else pc

    if "notice_period_type" in data and data["notice_period_type"]:
        npt = data["notice_period_type"]
        data["notice_period_type"] = npt.value if not isinstance(npt, str) else npt

    if "notice_period" in data and data["notice_period"]:
        np_val = data["notice_period"]
        data["notice_period"] = (
            np_val if not isinstance(np_val, str)
            else int(np_val) if str(np_val).isdigit()
            else None
        )

    # Create user
    raw_password = User.objects.make_random_password()
    user = User.objects.create_user(
        email=email,
        password=raw_password,
        first_name=first_name,
        last_name=last_name,
        phone_code=phone_code,
        phone_number=phone_number,
        gender=gender,  # Fix 1: pass the resolved value
        type=UserType.TALENT.value
    )
    user.is_active = True
    user.email_verified = True
    user.save()

    # Resolve FK objects
    country = None
    if country_uid:
        from accounts.models import Country
        country = Country.objects.filter(uid=country_uid).first()
        if not country:
            raise HttpError(400, "Invalid country")

    state = None
    if state_uid:
        from core.models import State
        state = State.objects.filter(uid=state_uid).first()
        if not state:
            raise HttpError(400, "Invalid state")

    role = None
    if role_uid:
        from accounts.models import Role
        role = Role.objects.filter(uid=role_uid).first()
        if not role:
            raise HttpError(400, "Invalid role")

    native_language = None
    if native_language_uid:
        from core.models import Language
        native_language = Language.objects.filter(uid=native_language_uid).first()
        if not native_language:
            raise HttpError(400, "Invalid native language")

    # Create talent
    talent = Talent.objects.create(
        user=user,
        country=country,
        state=state,
        role=role,
        native_language=native_language,
        **data
    )

    # M2M relationships
    if employment_type_uids:
        from jobs.models import EmploymentType
        employment_types = EmploymentType.objects.filter(uid__in=employment_type_uids)
        if employment_types.count() != len(employment_type_uids):
            raise HttpError(400, "One or more invalid employment types")
        talent.employment_types.set(employment_types)

    if additional_language_uids:
        from core.models import Language
        additional_languages = Language.objects.filter(uid__in=additional_language_uids)
        if additional_languages.count() != len(additional_language_uids):
            raise HttpError(400, "One or more invalid additional languages")
        talent.additional_languages.set(additional_languages)

    if skill_uids:
        from accounts.models import Skill
        skills = Skill.objects.filter(uid__in=skill_uids)
        if skills.count() != len(skill_uids):
            raise HttpError(400, "One or more invalid skills")
        talent.skills.set(skills)

    if business_model_uids:
        from jobs.models import BusinessModel
        business_models = BusinessModel.objects.filter(uid__in=business_model_uids)
        if business_models.count() != len(business_model_uids):
            raise HttpError(400, "One or more invalid business models")
        talent.business_models.set(business_models)

    # Nested objects
    if education_history:
        Education.objects.bulk_create([
            Education(**education, talent=talent)
            for education in education_history
        ])

    if experience_history:
        for experience in experience_history:
            if experience.get("salary_type"):
                st = experience["salary_type"]
                experience["salary_type"] = st.value if not isinstance(st, str) else st
            if experience.get("salary_bonus_type"):
                sbt = experience["salary_bonus_type"]
                experience["salary_bonus_type"] = sbt.value if not isinstance(sbt, str) else sbt
        Experience.objects.bulk_create([
            Experience(**experience, talent=talent)
            for experience in experience_history
        ])

    if availability:
        for available_day in availability:
            d = available_day["day"]
            available_day["day"] = d.value if not isinstance(d, str) else d
        TalentAvailableDay.objects.bulk_create([
            TalentAvailableDay(**available_day, talent=talent)
            for available_day in availability
        ])

    # Send emails
    async_task(
        send_admin_created_account_email,
        email=user.email,
        name=user.first_name,
        password=raw_password,
        account_type="talent"
    )

    Schedule.objects.create(
        func='helpers.email.accounts.send_incomplete_profile_reminder_email',
        schedule_type=Schedule.ONCE,
        next_run=timezone.now() + timedelta(days=1),
        kwargs=json.dumps({"emails": [user.email], "name": user.first_name})
    )

    return talent


def update_talent_years_of_experience(talent):
    years, month = talent.calculate_years_of_experience()
    avg_tenure = talent.calculate_avg_experience_tenure()
    talent.years_of_experience = years
    talent.months_of_experience = month
    talent.average_experience_tenure = avg_tenure
    talent.save(update_fields=["years_of_experience", "months_of_experience", "average_experience_tenure"])
    return talent


def application_to_interview(talent, start_date: date=None, end_date: date=None):
    total_interviews = talent.job_interviews(start_date=start_date, end_date=end_date).count()
    total_applications = talent.job_applications(start_date=start_date, end_date=end_date).count()
    return int((total_interviews/total_applications) * 100) if total_applications > 0 else 0


def total_interview_to_application(talent, start_date: date=None, end_date: date=None):
    total_interviews = talent.job_interviews(start_date=start_date, end_date=end_date).count()
    total_applications = talent.job_applications(start_date=start_date, end_date=end_date).count()
    return int((total_interviews/total_applications) * 100) if total_applications > 0 else 0

def recommended_jobs_count(talent):
    return get_talent_job_recommendations(talent, distinct=True).count()

def jobs_with_match_gt_50(talent, start_date: date=None, end_date: date=None):
    from jobs.models import JobPost
    from jobs.queries import add_job_post_annotations
    from jobs.enums import JobStatusType
    queryset = JobPost.objects.select_related("job", "country", "job__role", "job__created_by__business")
    if start_date and end_date:
        queryset = queryset.filter(job__created_at__range=[start_date, end_date])
    queryset = add_job_post_annotations(queryset, talent)
    queryset = queryset.filter(computed_match_score__gt=50, status=JobStatusType.POSTED.value)
    return queryset.annotate(
        row_number=Window(
            expression=RowNumber(),
            partition_by=[F("job_id")],
            order_by=[F("computed_match_score").desc()]  # highest score first
        )
    ).filter(row_number=1).count()


