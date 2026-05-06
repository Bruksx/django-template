from django.db.models import QuerySet, Exists, OuterRef, Q, Value, Case, When

from accounts.enums import TalentJobType
from accounts.models import Talent, Education, Experience, SkillCategory, TalentAvailableDay


def add_profile_completion_annotation(queryset:QuerySet[Talent]):
    # TalentSkill = Talent.skills.through
    TalentEmploymentTypes = Talent.employment_types.through
    all_category_ids = SkillCategory.objects.only("name").distinct("name").values_list("name", flat=True)
    # has_skills_filter = Q()
    # for cat in all_category_ids:
    #     has_skills_filter &= Q(Exists(TalentSkill.objects.filter(
    #         talent__id=OuterRef("id"), skill__category__name__iexact=cat))
    #     )
    return queryset.annotate(
        has_education=Exists(
            Education.objects.filter(talent_id=OuterRef("id")).exclude(
                Q(level__isnull=True) |
                Q(Q(major__isnull=True) | Q(major="")) |
                Q(Q(university__isnull=True) | Q(university="")) |
                Q(start_date__isnull=True)
            )
        ),
        has_experience=Exists(
            Experience.objects.filter(talent_id=OuterRef("id")).exclude(
                Q(role__isnull=True) |
                Q(Q(company__isnull=True) | Q(company="")) |
                Q(start_date__isnull=True) |
                Q(level__isnull=True)
            )
        ),
        has_availability=Exists(
            TalentAvailableDay.objects.filter(talent__id=OuterRef("id"))
    ),
        has_employment_types=Exists(
            TalentEmploymentTypes.objects.filter(talent__id=OuterRef("id"))
        ),
        has_basic_completeness=Case(
            When(
                Q(
                    Q(Q(user__first_name__isnull=False) & ~Q(user__first_name="")) &
                    Q(Q(user__last_name__isnull=False) & ~Q(user__last_name="")) &
                    Q(Q(user__email__isnull=False) & ~Q(user__email="")) &
                    Q(Q(user__phone_number__isnull=False) & ~Q(user__phone_number="")) &
                    Q(country__isnull=False)
                ),
                then=Value(True)
            ),
            default=Value(False)
        ),
        semi_complete_profile=Case(
            When(Q(has_basic_completeness=True, job_type=TalentJobType.SHIFT_JOBS.value), then=Value(True)),
            When(Q(has_basic_completeness=True, job_type=TalentJobType.FULL_TIME_JOBS.value, cv__isnull=False), then=Value(True))
            ,
            default=Value(False)
        ),
        complete_profile=Case(
            When(Q(semi_complete_profile=True, has_education=True,has_experience=True, has_employment_types=True) &
                Q(
                    Q(has_availability=True) | Q(flexible_availability=True)
                ) &
                Q(
                    Q(preferred_communication__isnull=False) &
                    Q(Q(work_models__isnull=False) & ~Q(work_models=[])) &
                    Q(Q(availability_timezone__isnull=False) & ~Q(availability_timezone="")) &
                    Q(native_language__isnull=False) &
                    Q(state__isnull=False) &
                    Q(role__isnull=False) &
                    Q(Q(postal_code__isnull=False) & ~Q(postal_code="")) &
                    Q(Q(bio__isnull=False) & ~Q(bio="")) &
                    Q(linkedin__isnull=False) &
                    Q(notice_period__isnull=False)
                ),
                then=Value(True)
            ),
            default=Value(False)
        ),


    )

