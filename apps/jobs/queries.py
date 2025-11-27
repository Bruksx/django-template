from django.db.models import (
    OuterRef, Exists, Case, When, Value, FloatField, Q, F, ExpressionWrapper, Count, Subquery, IntegerField,
    BooleanField, CharField
)
from django.db.models.functions import Coalesce, Cast
from django.db.models.query import QuerySet

from accounts.models import Talent, SkillCategory, Experience, Education, TalentAvailableDay
from jobs.models import (
    JobPost, RequiredAttribute, RequiredSecondaryLanguage, RequiredSkill, JobApplication, Job, AvailableDay,
)


def add_job_post_annotations(queryset: QuerySet[JobPost], talent: Talent) -> QuerySet[JobPost]:
    JobSkill = Job.skills.through
    RequiredBusinessModel = RequiredAttribute.business_models.through
    JobAddtionalLanguage = Job.additional_languages.through
    JobBusinessModel = Job.business_models.through
    talent_business_models = talent.business_models.all()
    talent_skill_ids = [i.id for i in talent.skills.all()]
    talent_additional_languages = talent.additional_languages.all()
    tools_platform_id = SkillCategory.objects.filter(name="Tools/Platforms").first().id
    methodologies_id = SkillCategory.objects.filter(name="Common Methodologies/Frameworks").first().id
    general_skills_id = SkillCategory.objects.filter(name="General Skills").first().id

    talent_gen_skills = talent.skills.filter(category__id=general_skills_id)
    talent_tools_skills = talent.skills.filter(category__id=tools_platform_id)
    talent_methodology_skills = talent.skills.filter(category=methodologies_id)

    required_attribute_subquery = RequiredAttribute.objects.filter(
        job=OuterRef("job")
    )

    queryset = queryset.annotate(
        requires_role=Exists(
            required_attribute_subquery.filter(role=True)
        ),
        prev_matching_role=Exists(Experience.objects.filter(talent=talent, role=OuterRef("job__role"))),
        matching_role=Case(
            When(Q(prev_matching_role=True) | Q(job__role=talent.role), then=Value(True)),
            default=False,
            output_field=BooleanField()
        ),
        role_score=Case(
            When(
                Q(Q(matching_role=True) | Q(prev_matching_role=True)),
                then=Value(6.67)
            ),
            default=Value(0.0),
            output_field=FloatField()
        )
    ).annotate(
        missing_required_skill=Exists(
            RequiredSkill.objects.exclude(skill__id__in=talent_skill_ids).filter(required_attribute__job=OuterRef("job"))
        )
    ).annotate(
        gen_skill_count=Subquery(
            JobSkill.objects
                .filter(
                    job=OuterRef("job"),
                    skill__category__id=general_skills_id,
                )
                .values("job_id")             # group by job
                .annotate(count=Count("id"))  # count matching rows
                .values("count")[:1]          # select the count
        ),
        gen_skill_intercept_count=Coalesce(Subquery(
            JobSkill.objects
                .filter(
                    job=OuterRef("job"),
                    skill__category__id=general_skills_id,
                    skill_id__in=talent_gen_skills,
                )
                .values("job_id")           # group by job
                .annotate(count=Count("id"))   # count matching rows
                .values("count")[:1]           # select just the count
        ), Value(0), output_field=IntegerField()),
        general_skill_score=Case(
            When(Q(gen_skill_count=None), then=Value(6.67)),
            default=(F("gen_skill_intercept_count") * Value(6.67) ) / F("gen_skill_count") ,
            output_field=FloatField()
        )
    ).annotate(
        tools_platform_count=Subquery(
            JobSkill.objects
                .filter(
                    job=OuterRef("job"),
                    skill__category__id=tools_platform_id,
                )
                .values("job_id")             # group by job
                .annotate(count=Count("id"))  # count matching rows
                .values("count")[:1]          # select the count
        ),
        tools_platform_intercept_count=Subquery(
            JobSkill.objects
                .filter(
                    job=OuterRef("job"),
                    skill__category__id=tools_platform_id,
                    skill_id__in=talent_tools_skills,
                )
                .values("job_id")           # group by applicant
                .annotate(count=Count("id"))   # count matching rows
                .values("count")[:1]           # select just the count
        ),
        tools_platform_score=Case(
            When(Q(tools_platform_count=None), then=Value(6.67)),
            default=(F("tools_platform_intercept_count") * Value(6.67) ) / F("tools_platform_count") ,
            output_field=FloatField()
        )
    ).annotate(
        methodologies_count=Subquery(
            JobSkill.objects
                .filter(
                    job=OuterRef("job"),
                    skill__category__id=methodologies_id,
                )
                .values("job_id")             # group by job
                .annotate(count=Count("id"))  # count matching rows
                .values("count")[:1]          # select the count
        ),
        methodologies_intercept_count=Coalesce(Subquery(
            JobSkill.objects
                .filter(
                    job=OuterRef("job"),
                    skill__category__id=methodologies_id,
                    skill_id__in=talent_methodology_skills,
                )
                .values("job_id")           # group by applicant
                .annotate(count=Count("id"))   # count matching rows
                .values("count")[:1]           # select just the count
        ), Value(0), output_field=IntegerField()),
        methodologies_score=Case(
            When(Q(methodologies_count=None), then=Value(6.67)),
            default=(F("methodologies_intercept_count") * Value(6.67) ) / F("methodologies_count") ,
            output_field=FloatField()
        )
    ).annotate(
        business_model_count=Subquery(
            JobBusinessModel.objects.filter(
                job=OuterRef("job")
            )
            .values("job_id")             # group by job
            .annotate(count=Count("id"))  # count matching rows
            .values("count")[:1]          # select the count
        ),
        matching_business_model_count=Coalesce(Subquery(
            JobBusinessModel.objects.filter(
                job=OuterRef("job"), 
                businessmodel__in=talent_business_models
            )
            .values("job_id")             # group by job
            .annotate(count=Count("id"))  # count matching rows
            .values("count")[:1]          # select the count
        ), Value(0), output_field=IntegerField()),
        business_model_score=Case(
            When(business_model_count=None, then=Value(6.67)),
            default=(F("matching_business_model_count") * Value(6.67)) / F("business_model_count") ,
            output_field=FloatField(),
        ),
        missing_required_business_model=Exists(
            RequiredBusinessModel.objects.exclude(businessmodel__in=talent_business_models).filter(requiredattribute__job=OuterRef("job"))
        )
    ).annotate(
        requires_job_level=Exists(
        required_attribute_subquery.filter(job_level=True)
    ),
        has_matching_experience=Exists(
        Experience.objects.filter(
            talent=talent,
            level=OuterRef("job__job_level")
        )
    ),
        job_level_score=Case(
            When(
                Q(has_matching_experience=True),
                then=Value(6.67)
            ),
            default=Value(0.0),
            output_field=FloatField()
        )
    ).annotate(
        requires_experience=Exists(
            required_attribute_subquery.filter(years_of_experience=True)
        ),
        meets_experience=Case(
            When(job__years_of_experience__isnull=True, then=Value(True)),
            When(job__years_of_experience__lte=talent.years_of_experience, then=Value(True)),
            default=Value(False),
            output_field=BooleanField()
        ),
        experience_score=Case(
            When(
                Q(meets_experience=True), 
                then=Value(6.67)
            ),
            default=Value(0.0),
            output_field=FloatField()
        )
    ).annotate(
        requires_minimum_education=Exists(
            required_attribute_subquery.filter(minimum_education_level=True)
        ),
        has_minimum_education_requirement=Exists(
            Education.objects.filter(talent=talent, level__order__gte=OuterRef("job__minimum_education_level__order"))
        ),
        minimum_education_score=Case(
            When(job__minimum_education_level=None, then=Value(6.67)),
            When(has_minimum_education_requirement=True, then=Value(6.67)),
            default=Value(0.0),
            output_field=FloatField()
        )
    ).annotate(
        requires_work_structure=Exists(
            required_attribute_subquery.filter(work_structure=True)
        ),
        work_structure_score=Case(
            When(
                Q(job__work_structure__in=talent.work_models),
                then=Value(6.67)
            ),
            default=Value(0.0),
            output_field=FloatField()
        )
    ).annotate(
        requires_tech_requirements=Exists(
            required_attribute_subquery.filter(technological_requirement=True)
        ),
        meets_tech_requirements=Case(
            When(
                Q(job__technological_requirement="undetermined"), then=Value(True),
            ),
            When(Q(job__technological_requirement__isnull=True), then=Value(True)),
            default=Value(False),
            output_field=BooleanField(),
        ),
        tech_requirement_score=Case(
            When(meets_tech_requirements=True, then=Value(6.67)),
            default=Value(0.0),
            output_field=FloatField()
        )
    ).annotate(
        requires_first_language=Exists(
            required_attribute_subquery.filter(first_language=True),
        ),
        first_language_score=Case(
            When(requires_first_language=False, then=6.67),
            When(
                Q(requires_first_language=True) & Q(job__first_language=talent.native_language),
                then=Value(6.67)
            ),
            default=Value(0.0),
            output_field=FloatField()
        )
    ).annotate(
        job_additional_language_count=Subquery(
            JobAddtionalLanguage.objects.filter(
                job=OuterRef("job")
            )
            .values("job_id")             # group by job
            .annotate(count=Count("id"))  # count matching rows
            .values("count")[:1]          # select the count
        ),
        matching_additional_languages=Subquery(
            JobAddtionalLanguage.objects.filter(
                job=OuterRef("job"),
                language__in=talent_additional_languages
            )
            .values("job_id")             # group by job
            .annotate(count=Count("id"))  # count matching rows
            .values("count")[:1]          # select the count
        ),
        additional_language_score = Case(
            When(
                job_additional_language_count=None,
                then=Value(6.67)
            ),
            default=(F("matching_additional_languages") * Value(6.67)) / F("job_additional_language_count"),
            output_field=FloatField()
        )
    ).annotate(
        missing_compulsory_secondary_language=Exists(
            RequiredSecondaryLanguage.objects.filter(
                required_attribute__job=OuterRef("job")
            ).exclude(id__in=talent_additional_languages)
        )
    ).annotate(
        available_days_count=Subquery(
            AvailableDay.objects
                .filter(job=OuterRef("job"))
                .values("job_id")             # group by job
                .annotate(count=Count("id"))  # count rows
                .values("count")[:1]          # return the count
        ),
        matching_days_count=Subquery(
            AvailableDay.objects.filter(
                job=OuterRef("job")
            )
            .annotate(
                day_match_exists=Exists(
                    TalentAvailableDay.objects.filter(
                        talent=talent,
                        day=OuterRef("day"),
                        utc_start_time__gte=OuterRef("utc_start_time"),
                        utc_end_time__lte=OuterRef("utc_end_time"),
                    )
                )
            )
            .filter(day_match_exists=True)
            .values("job_id")               # group by job
            .annotate(cnt=Count("id"))      # count matching days
            .values("cnt")[:1],             # only return the count column
            output_field=IntegerField()
        ),
        work_schedule_score=Case(
            When(available_days_count=None, then=Value(6.67)),
            default=(F("matching_days_count") * Value(6.67)) /F("available_days_count") ,
            output_field=FloatField()
        )
    ).annotate(
        flexible_talent=Exists(Talent.objects.filter(id=talent.id, flexible_availability=True)),
        final_work_schedule_score=Case(
            When(Q(flexible_talent=True) | Q(job__flexible_availability=True), then=Value(6.67)),
            default=ExpressionWrapper(F("work_schedule_score"), output_field=FloatField()),
            output_field=FloatField(),
        )
    ).annotate(
        requires_work_schedule=Exists(required_attribute_subquery.filter(working_hours=True)),
        missing_work_schedule=Case(
            When(Q(requires_work_schedule=True) & Q(work_schedule_score__lt=6.67), then=Value(True)),
            output_field=BooleanField(),
            default=Value(False)
        )
    ).annotate(
        requires_location=Exists(required_attribute_subquery.filter(location=True)),
        location_score=Case(
            When(Q(country=talent.country), then=Value(6.67)),
            default=Value(0.0),
            output_field=FloatField()
        )
    ).annotate(
        computed_match_score=Case(
            When(Q(requires_location=True) & Q(location_score=0.0), then=Value(0.0)),
            When(missing_compulsory_secondary_language=True, then=Value(0.0)),
            When(Q(requires_role=True) & Q(matching_role=False), then=Value(0.0)),
            When(Q(missing_required_skill=True), then=Value(0.0)),
            When(Q(requires_job_level=True) & Q(has_matching_experience=False), then=Value(0.0)),
            When(Q(requires_experience=True) & Q(meets_experience=False), then=Value(0.0)),
            When(Q(requires_minimum_education=True) & Q(has_minimum_education_requirement=False), then=Value(0.0)),
            When(Q(requires_work_structure=True) & Q(job__work_structure__in=talent.work_models), then=Value(0.0)),
            When(Q(requires_tech_requirements=True) & Q(meets_tech_requirements=False), then=Value(0.0)),
            When(Q(missing_work_schedule=True), then=Value(0.0)),
            When(Q(missing_required_business_model=True), then=Value(0.0)),
            default=ExpressionWrapper(
                Cast(Coalesce(F("role_score"), 0.0), FloatField()) +
                Cast(Coalesce(F("business_model_score"), 0.0), FloatField()) + 
                Cast(Coalesce(F("tools_platform_score"), 0.0), FloatField()) +
                Cast(Coalesce(F("methodologies_score"), 0.0), FloatField()) +
                Cast(Coalesce(F("general_skill_score"), 0.0), FloatField()) +
                Cast(Coalesce(F("job_level_score"), 0.0), FloatField()) +
                Cast(Coalesce(F("experience_score"), 0.0), FloatField()) +
                Cast(Coalesce(F("minimum_education_score"), 0.0), FloatField()) +
                Cast(Coalesce(F("work_structure_score"), 0.0), FloatField()) +
                Cast(Coalesce(F("tech_requirement_score"), 0.0), FloatField()) +
                Cast(Coalesce(F("first_language_score"), 0.0), FloatField()) +
                Cast(Coalesce(F("additional_language_score"), 0.0), FloatField()) +
                Cast(Coalesce(F("final_work_schedule_score"), 0.0), FloatField()) +
                Cast(Coalesce(F("location_score"), 0.0), FloatField()),
                output_field=FloatField(),
            ),
        output_field=FloatField(),
    )
    )
    return queryset


def add_application_match_score(queryset: QuerySet[JobApplication], job_post:JobPost) -> QuerySet[JobApplication]:
    TalentSkill = Talent.skills.through
    JobSkill = Job.skills.through
    TalentBusinessModel = Talent.business_models.through
    RequiredBusinessModel = RequiredAttribute.business_models.through
    JobBusinessModel = Job.business_models.through
    ApplicantAdditionalLanguage = Talent.additional_languages.through
    required_attribute = job_post.job.requiredattribute
    required_skill_ids = [i.skill.id for i in RequiredSkill.objects.filter(required_attribute=required_attribute)]
    required_skill_count = len(required_skill_ids)
    general_skills_id = SkillCategory.objects.filter(name="General Skills").first().id
    tools_platform_id = SkillCategory.objects.filter(name="Tools/Platforms").first().id
    methodologies_id = SkillCategory.objects.filter(name="Common Methodologies/Frameworks").first().id
    job_work_structure = job_post.job.work_structure
    job_additional_languages = job_post.job.additional_languages.all()
    required_language_ids = [i.language.id for i in RequiredSecondaryLanguage.objects.filter(required_attribute__job=job_post.job)]

    job_gen_skills = job_post.job.skills.filter(category__id=general_skills_id)
    job_tools_skills = job_post.job.skills.filter(category__id=tools_platform_id)
    job_methodology_skills = job_post.job.skills.filter(category=methodologies_id)

    job_business_models = [i.id for i in job_post.job.business_models.all()]
    job_required_business_models = [i.id for i in RequiredBusinessModel.objects.filter(requiredattribute=required_attribute)]

    required_attribute_subquery = RequiredAttribute.objects.filter(
        job=OuterRef("job_post__job")
    )

    queryset = queryset.annotate(
        requires_role=Exists(
            required_attribute_subquery.filter(role=True)
        ),
        prev_matching_role=Exists(Experience.objects.filter(talent=OuterRef("applicant"), role=OuterRef("job_post__job__role"))),
        matching_role=Case(
            When(Q(prev_matching_role=True) | Q(job_post__job__role=F("applicant__role")), then=Value(True)),
            default=False,
            output_field=BooleanField()
        ),
        role_score=Case(
            When(
                Q(matching_role=True),
                then=Value(6.67)
            ),
            default=Value(0.0),
            output_field=FloatField()
        )
    ).annotate(
        talent_required_skill_count=Subquery(
            TalentSkill.objects
                .filter(
                    talent_id=OuterRef("applicant__id"),
                    skill_id__in=required_skill_ids,
                )
                .values("talent_id")           # group by applicant
                .annotate(count=Count("id"))   # count matching rows
                .values("count")[:1]           # return the count
        ),
        missing_required_skill=Case(
            When(
                Q(talent_required_skill_count__lt=required_skill_count),
                then=Value(True)
            ),
            default=Value(False),
            output_field=BooleanField()
        )
    ).annotate(
        gen_skill_count=Subquery(
            JobSkill.objects
                .filter(
                    job=OuterRef("job_post__job"),
                    skill__category__id=general_skills_id,
                )
                .values("job_id")             # group by job
                .annotate(count=Count("id"))  # count matching rows
                .values("count")[:1]          # select the count
        ),
        gen_skill_intercept_count=Subquery(
            TalentSkill.objects
                .filter(
                    talent=OuterRef("applicant"),
                    skill__category__id=general_skills_id,
                    skill_id__in=job_gen_skills,
                )
                .values("talent_id")           # group by applicant
                .annotate(count=Count("id"))   # count matching rows
                .values("count")[:1]           # select just the count
        ),
        general_skill_score=Case(
            When(Q(gen_skill_count=None), then=Value(6.67)),
            default=(F("gen_skill_intercept_count") * Value(6.67) ) / F("gen_skill_count") ,
            output_field=FloatField()
        )
    ).annotate(
        tools_platform_count=Subquery(
            JobSkill.objects
                .filter(
                    job=OuterRef("job_post__job"),
                    skill__category__id=tools_platform_id,
                )
                .values("job_id")             # group by job
                .annotate(count=Count("id"))  # count matching rows
                .values("count")[:1]          # select the count
        ),
        tools_platform_intercept_count=Subquery(
            TalentSkill.objects
                .filter(
                    talent=OuterRef("applicant"),
                    skill__category__id=tools_platform_id,
                    skill_id__in=job_tools_skills,
                )
                .values("talent_id")           # group by applicant
                .annotate(count=Count("id"))   # count matching rows
                .values("count")[:1]           # select just the count
        ),
        tools_platform_score=Case(
            When(Q(tools_platform_count=None), then=Value(6.67)),
            default=(F("tools_platform_intercept_count") * Value(6.67) ) / F("tools_platform_count") ,
            output_field=FloatField()
        )
    ).annotate(
        methodologies_count=Subquery(
            JobSkill.objects
                .filter(
                    job=OuterRef("job_post__job"),
                    skill__category__id=methodologies_id,
                )
                .values("job_id")             # group by job
                .annotate(count=Count("id"))  # count matching rows
                .values("count")[:1]          # select the count
        ),
        methodologies_intercept_count=Subquery(
            TalentSkill.objects
                .filter(
                    talent=OuterRef("applicant"),
                    skill__category__id=methodologies_id,
                    skill__in=job_methodology_skills,
                )
                .values("talent_id")           # group by applicant
                .annotate(count=Count("id"))   # count matching rows
                .values("count")[:1]           # select just the count
        ),
        methodologies_score=Case(
            When(Q(methodologies_count=None), then=Value(6.67)),
            default=ExpressionWrapper(
                (F("methodologies_intercept_count") / F("methodologies_count")) * Value(6.67),
                output_field=FloatField()
            ),
            output_field=FloatField()
        )
    ).annotate(
        business_model_count=Subquery(
            JobBusinessModel.objects.filter(
                job=OuterRef("job_post__job")
            )
            .values("job_id")             # group by job
            .annotate(count=Count("id"))  # count matching rows
            .values("count")[:1]          # select the count
        ),
        matching_business_model_count=Subquery(
            TalentBusinessModel.objects.filter(
                talent=OuterRef("applicant"), 
                businessmodel_id__in=job_business_models
            )
            .values("talent_id")          # group by talent
            .annotate(count=Count("id"))  # count matching rows
            .values("count")[:1]          # select the count
        ),
        business_model_score=Case(
            When(business_model_count=None, then=Value(6.67)),
            default=(F("matching_business_model_count") * Value(6.67)) / F("business_model_count") ,
            output_field=FloatField(),
        ),
        matching_required_business_model_count=Subquery(
            TalentBusinessModel.objects.filter(
                talent=OuterRef("applicant"), 
                businessmodel__in=job_required_business_models
            )
            .values("talent_id")          # group by talent
            .annotate(count=Count("id"))  # count matching rows
            .values("count")[:1]          # select the count
        ),
        missing_required_business_model=Case(
            When(matching_required_business_model_count__lt=len(job_required_business_models), then=Value(True)),
            default=Value(False),
            output_field=BooleanField(),
        )
    ).annotate(
        requires_job_level=Exists(
        required_attribute_subquery.filter(job_level=True)
    ),
        has_matching_experience=Exists(
        Experience.objects.filter(
            talent=OuterRef("applicant"),
            level=OuterRef("job_post__job__job_level")
        )
    ),
        job_level_score=Case(
            When(
                Q(has_matching_experience=True),
                then=Value(6.67)
            ),
            default=Value(0.0),
            output_field=FloatField()
        )
    ).annotate(
        requires_experience=Exists(
            required_attribute_subquery.filter(years_of_experience=True)
        ),
        meets_experience=Case(
            When(job_post__job__years_of_experience__isnull=True, then=Value(True)),
            When(job_post__job__years_of_experience__lte=F("applicant__years_of_experience"), then=Value(True)),
            default=Value(False),
            output_field=BooleanField()
        ),
        experience_score=Case(
            When(
                Q(meets_experience=True), 
                then=Value(6.67)
            ),
            default=Value(0.0),
            output_field=FloatField()
        )
    ).annotate(
        requires_minimum_education=Exists(
            required_attribute_subquery.filter(minimum_education_level=True)
        ),
        has_minimum_education_requirement=Exists(
            Education.objects.filter(talent=OuterRef("applicant"), level__order__gte=OuterRef("job_post__job__minimum_education_level__order"))
        ),
        minimum_education_score=Case(
            When(job_post__job__minimum_education_level=None, then=Value(6.67)),
            When(has_minimum_education_requirement=True, then=Value(6.67)),
            default=Value(0.0),
            output_field=FloatField()
        )
    ).annotate(
        requires_work_structure=Exists(
            required_attribute_subquery.filter(work_structure=True)
        ),
        work_structure_match=Exists(
            Talent.objects.filter(
                id=OuterRef("applicant_id"),
                work_models__contains=[job_work_structure]
            )
        ),
        work_structure_score=Case(
            When(
                Q(work_structure_match=True),
                then=Value(6.67)
            ),
            default=Value(0.0),
            output_field=FloatField()
        )
    ).annotate(
        requires_tech_requirements=Exists(
            required_attribute_subquery.filter(technological_requirement=True)
        ),
        meets_tech_requirements=Case(
            When(
                Q(job_post__job__technological_requirement="undetermined"),
                then=Value(True),
            ),
            When(Q(job_post__job__technological_requirement=None),
                then=Value(True),
            ),
            default=Value(False),
            output_field=BooleanField(),
        ),
        tech_requirement_score=Case(
            When(meets_tech_requirements=True, then=Value(6.67)),
            default=Value(0.0),
            output_field=FloatField()
        )
    ).annotate(
        requires_first_language=Exists(
            required_attribute_subquery.filter(first_language=True),
        ),
        first_language_score=Case(
            When(job_post__job__first_language=None, then=6.67),
            When(
                Q(job_post__job__first_language=F("applicant__native_language")),
                then=Value(6.67)
            ),
            default=Value(0.0),
            output_field=FloatField()
        )
    ).annotate(
        job_additional_language_count=Count("job_post__job__additional_languages"),
        matching_additional_languages=Subquery(
            ApplicantAdditionalLanguage.objects
                .filter(
                    talent_id=OuterRef("applicant_id"),
                    language__in=job_additional_languages,
                )
                .values("talent_id")        # group by applicant
                .annotate(count=Count("id"))  # count matches
                .values("count")[:1]        # return the count
        ),
        additional_language_score = Case(
            When(
                job_additional_language_count=0,
                then=Value(6.67)
            ),
            default=(F("matching_additional_languages") * Value(6.67)) / F("job_additional_language_count"),
            output_field=FloatField()
        )
    ).annotate(
        matching_compulsory_additional_languages=Count("applicant__additional_languages", filter=Q(applicant__additional_languages__in=required_language_ids)),
        missing_compulsory_secondary_language=Case(
            When(matching_compulsory_additional_languages__lt=len(required_language_ids), then=Value(True)),
            output_field=BooleanField(),
            default=Value(False)
        )
    ).annotate(
        available_days_count=Subquery(
            AvailableDay.objects
                .filter(job=job_post.job)
                .values("job_id")             # group by job
                .annotate(count=Count("id"))  # count rows
                .values("count")[:1]          # return the count
        ),
        matching_days_count=Subquery(
            TalentAvailableDay.objects.filter(
                talent=OuterRef("applicant")
            )
            .annotate(
                day_match_exists=Exists(
                    AvailableDay.objects.filter(
                        job=job_post.job,
                        day=OuterRef("day"),
                        utc_start_time__gte=OuterRef("utc_start_time"),
                        utc_end_time__lte=OuterRef("utc_end_time"),
                    )
                )
            )
            .filter(day_match_exists=True)
            .values("talent")               # group by talent
            .annotate(cnt=Count("id"))      # count matching days
            .values("cnt")[:1],             # only return the count column
            output_field=IntegerField()
        ),
        work_schedule_score=Case(
            When(available_days_count=None, then=Value(6.67)),
            default=(F("matching_days_count") * Value(6.67)) /F("available_days_count") ,
            output_field=FloatField()
        )
    ).annotate(
        final_work_schedule_score=Case(
            When(Q(applicant__flexible_availability=True) | Q(job_post__job__flexible_availability=True), then=Value(6.67)),
            default=F("work_schedule_score"),
            output_field=FloatField(),
        )
    ).annotate(
        requires_work_schedule=Exists(required_attribute_subquery.filter(working_hours=True)),
        missing_work_schedule=Case(
            When(Q(requires_work_schedule=True) & Q(work_schedule_score__lt=6.67), then=Value(True)),
            output_field=BooleanField(),
            default=Value(False)
        )
    ).annotate(
        requires_location=Exists(required_attribute_subquery.filter(location=True)),
        location_score=Case(
            When(applicant__country=job_post.country, then=Value(6.67)),
            default=Value(0.0),
            output_field=FloatField()
        )
    ).annotate(
        computed_match_score=Case(
            When(Q(requires_location=True) & Q(location_score=0.0), then=Value(0.0)),
            When(missing_compulsory_secondary_language=True, then=Value(0.0)),
            When(Q(requires_role=True) & Q(matching_role=False), then=Value(0.0)),
            When(Q(missing_required_skill=True), then=Value(0.0)),
            When(Q(requires_job_level=True) & Q(has_matching_experience=False), then=Value(0.0)),
            When(Q(requires_experience=True) & Q(meets_experience=False), then=Value(0.0)),
            When(Q(requires_minimum_education=True) & Q(has_minimum_education_requirement=False), then=Value(0.0)),
            When(Q(requires_work_structure=True) & Q(work_structure_match=False), then=Value(0.0)),
            When(Q(requires_tech_requirements=True) & Q(meets_tech_requirements=False), then=Value(0.0)),
            When(Q(missing_work_schedule=True), then=Value(0.0)),
            When(Q(missing_required_business_model=True), then=Value(0.0)),
            default=ExpressionWrapper(
                Cast(F("role_score"), FloatField()) +
                Cast(F("tools_platform_score"), FloatField()) +
                Cast(F("methodologies_score"), FloatField()) +
                Cast(F("general_skill_score"), FloatField()) +
                Cast(F("job_level_score"), FloatField()) +
                Cast(F("experience_score"), FloatField()) +
                Cast(F("business_model_score"), FloatField()) +
                Cast(F("minimum_education_score"), FloatField()) +
                Cast(F("work_structure_score"), FloatField()) +
                Cast(F("tech_requirement_score"), FloatField()) +
                Cast(F("first_language_score"), FloatField()) +
                Cast(F("additional_language_score"), FloatField()) +
                Cast(F("final_work_schedule_score"), FloatField()) +
                Cast(F("location_score"), FloatField()),
                output_field=FloatField(),
            ),
            output_field=FloatField(),
        )
    )

    return queryset

def add_talent_match_score(queryset: QuerySet[Talent], job_post:JobPost) -> QuerySet[Talent]:
    TalentSkill = Talent.skills.through
    JobSkill = Job.skills.through
    TalentBusinessModel = Talent.business_models.through
    JobBusinessModel = Job.business_models.through
    ApplicantAdditionalLanguage = Talent.additional_languages.through
    required_attribute = job_post.job.requiredattribute
    required_skill_ids = [i.skill.id for i in RequiredSkill.objects.filter(required_attribute=required_attribute)]
    required_skill_count = len(required_skill_ids)
    general_skills_id = SkillCategory.objects.filter(name="General Skills").first().id
    tools_platform_id = SkillCategory.objects.filter(name="Tools/Platforms").first().id
    methodologies_id = SkillCategory.objects.filter(name="Common Methodologies/Frameworks").first().id
    job_work_structure = job_post.job.work_structure
    job_additional_languages = job_post.job.additional_languages.all()
    job_gen_skills = job_post.job.skills.filter(category__id=general_skills_id)
    job_tools_skills = job_post.job.skills.filter(category__id=tools_platform_id)
    job_methodology_skills = job_post.job.skills.filter(category=methodologies_id)

    job_business_models = [i.id for i in job_post.job.business_models.all()]
    required_attribute_subquery = RequiredAttribute.objects.filter(
        job=job_post.job
    )
    queryset = queryset.annotate(
        requires_role=Exists(
            required_attribute_subquery.filter(role=True)
        ),
        prev_matching_role=Exists(Experience.objects.filter(talent_id=OuterRef("id"), role=job_post.job.role)),
        matching_role=Case(
            When(Q(prev_matching_role=True) | Q(role=job_post.job.role) , then=Value(True)),
            default=False,
            output_field=BooleanField()
        ),
        role_score=Case(
            When(
                Q(Q(matching_role=True)|Q(prev_matching_role=True)),
                then=Value(6.67)
            ),
            default=Value(0.0),
            output_field=FloatField()
        )
    ).annotate(
        talent_required_skill_count=Coalesce(Subquery(
            TalentSkill.objects
                .filter(
                    talent_id=OuterRef("id"),
                    skill_id__in=required_skill_ids,
                )
                .values("talent_id")           # group by applicant
                .annotate(count=Count("id"))   # count matching rows
                .values("count")[:1]           # return the count
        ), Value(0), output_field=IntegerField()),
        missing_required_skill=Case(
            When(
                Q(talent_required_skill_count__lt=required_skill_count),
                then=Value(True)
            ),
            default=Value(False),
            output_field=BooleanField()
        )
    ).annotate(
        gen_skill_count=Subquery(
            JobSkill.objects
                .filter(
                    job=job_post.job,
                    skill__category__id=general_skills_id,
                )
                .values("job_id")             # group by job
                .annotate(count=Count("id"))  # count matching rows
                .values("count")[:1]          # select the count
        ),
        gen_skill_intercept_count=Subquery(
            TalentSkill.objects
                .filter(
                    talent_id=OuterRef("id"),
                    skill__category__id=general_skills_id,
                    skill_id__in=job_gen_skills,
                )
                .values("talent_id")           # group by applicant
                .annotate(count=Count("id"))   # count matching rows
                .values("count")[:1]           # select just the count
        ),
        general_skill_score=Case(
            When(Q(gen_skill_count=None), then=Value(6.67)),
            default=(F("gen_skill_intercept_count") * Value(6.67) ) / F("gen_skill_count") ,
            output_field=FloatField()
        )
    ).annotate(
        tools_platform_count=Subquery(
            JobSkill.objects
                .filter(
                    job=job_post.job,
                    skill__category__id=tools_platform_id,
                )
                .values("job_id")             # group by job
                .annotate(count=Count("id"))  # count matching rows
                .values("count")[:1]          # select the count
        ),
        tools_platform_intercept_count=Subquery(
            TalentSkill.objects
                .filter(
                    talent_id=OuterRef("id"),
                    skill__category__id=tools_platform_id,
                    skill_id__in=job_tools_skills,
                )
                .values("talent_id")           # group by applicant
                .annotate(count=Count("id"))   # count matching rows
                .values("count")[:1]           # select just the count
        ),
        tools_platform_score=Case(
            When(Q(tools_platform_count=None), then=Value(6.67)),
            default=(F("tools_platform_intercept_count") * Value(6.67) ) / F("tools_platform_count") ,
            output_field=FloatField()
        )
    ).annotate(
        methodologies_count=Subquery(
            JobSkill.objects
                .filter(
                    job=job_post.job,
                    skill__category__id=methodologies_id,
                )
                .values("job_id")             # group by job
                .annotate(count=Count("id"))  # count matching rows
                .values("count")[:1]          # select the count
        ),
        methodologies_intercept_count=Coalesce(Subquery(
            TalentSkill.objects
                .filter(
                    talent_id=OuterRef("id"),
                    skill__category__id=methodologies_id,
                    skill__in=job_methodology_skills,
                )
                .values("talent_id")           # group by applicant
                .annotate(count=Count("id"))   # count matching rows
                .values("count")[:1]           # select just the count
        ), Value(0), output_field=IntegerField()),
        methodologies_score=Case(
            When(Q(methodologies_count=None), then=Value(6.67)),
            default=(F("methodologies_intercept_count") * Value(6.67) ) / F("methodologies_count"),
            output_field=FloatField()
            ),
    ).annotate(
        business_model_count=Subquery(
            JobBusinessModel.objects.filter(
                job=job_post.job
            )
            .values("job_id")             # group by job
            .annotate(count=Count("id"))  # count matching rows
            .values("count")[:1]          # select the count
        ),
        matching_business_model_count=Coalesce(Subquery(
            TalentBusinessModel.objects.filter(
                talent_id=OuterRef("id"),
                businessmodel_id__in=job_business_models
            )
            .values("talent_id")          # group by talent
            .annotate(count=Count("id"))  # count matching rows
            .values("count")[:1]          # select the count
        ), Value(0), output_field=IntegerField()),
        business_model_score=Case(
            When(business_model_count__isnull=True, then=Value(6.67)),
            default=(F("matching_business_model_count") * Value(6.67)) / F("business_model_count") ,
            output_field=FloatField(),
        ),
        matching_required_business_model_count=Coalesce(Subquery(
            TalentBusinessModel.objects.filter(
                talent_id=OuterRef("id"),
                businessmodel__id__in=job_business_models
            )
            .values("talent_id")          # group by talent
            .annotate(count=Count("id"))  # count matching rows
            .values("count")[:1]          # select the count
        ), Value(0), output_field=IntegerField()),
        missing_required_business_model=Case(
            When(matching_required_business_model_count__lt=len(job_business_models), then=Value(True)),
            default=Value(False),
            output_field=BooleanField(),
        )
    ).annotate(
        requires_job_level=Exists(
        required_attribute_subquery.filter(job_level=True)
    ),
        has_matching_experience=Exists(
        Experience.objects.filter(
            talent_id=OuterRef("id"),
            level=job_post.job.job_level
        )
    ),
        job_level_score=Case(
            When(
                Q(has_matching_experience=True),
                then=Value(6.67)
            ),
            default=Value(0.0),
            output_field=FloatField()
        )
    ).annotate(
        job_years_of_experience=Value(job_post.job.years_of_experience, output_field=IntegerField(null=True)),
        requires_experience=Exists(
            required_attribute_subquery.filter(years_of_experience=True)
        ),
        meets_experience=Case(
            When(job_years_of_experience__isnull=True, then=Value(True)),
            When(years_of_experience__isnull=True, then=Value(False)),
            When(years_of_experience__gte=Coalesce(job_post.job.years_of_experience, Value(0)), then=Value(True)),
            default=Value(False),
            output_field=BooleanField()
        ),
        experience_score=Case(
            When(
                Q(meets_experience=True),
                then=Value(6.67)
            ),
            default=Value(0.0),
            output_field=FloatField()
        )
    ).annotate(
        requires_minimum_education=Exists(
            required_attribute_subquery.filter(minimum_education_level=True)
        ),
        has_minimum_education_requirement=Exists(
            Education.objects.filter(talent_id=OuterRef("id"), level__order__gte=Value(job_post.job.minimum_education_level.order if job_post.job.minimum_education_level else -1, output_field=IntegerField()))
        ),
        minimum_education_score=Case(
            When(has_minimum_education_requirement=True, then=Value(6.67)),
            When(has_minimum_education_requirement=False, then=Value(0.0)),
            default=Value(6.67),
            output_field=FloatField()
        )
    ).annotate(
        requires_work_structure=Exists(
            required_attribute_subquery.filter(work_structure=True)
        ),
        work_structure_match=Exists(
            Talent.objects.filter(
                id=OuterRef("id"),
                work_models__contains=[job_work_structure]
            )
        ),
        work_structure_score=Case(
            When(
                Q(work_structure_match=True),
                then=Value(6.67)
            ),
            default=Value(0.0),
            output_field=FloatField()
        )
    ).annotate(
        requires_tech_requirements=Exists(
            required_attribute_subquery.filter(technological_requirement=True)
        ),
        job_technological_requirement=Value(job_post.job.technological_requirement, output_field=CharField(null=True)),
        meets_tech_requirements=Case(
            When(
                Q(job_technological_requirement="undetermined"),
                then=Value(True),
            ),
            When(Q(job_technological_requirement__isnull=True),
                 then=Value(True),
                 ),
            default=Value(False),
            output_field=BooleanField(),
        ),
        tech_requirement_score=Case(
            When(meets_tech_requirements=True, then=Value(6.67)),
            default=Value(0.0),
            output_field=FloatField()
        )
    ).annotate(
        requires_first_language=Exists(
            required_attribute_subquery.filter(first_language=True),
        ),
        first_language_score=Case(
            When(requires_first_language=False, then=6.67),
            When(native_language=job_post.job.first_language, then=Value(6.67),
                 ),
            When(~Q(native_language=job_post.job.first_language), then=Value(0.0)),
            default=Value(6.67),
            output_field=FloatField()
        )
    ).annotate(
        matching_additional_languages=Subquery(
            ApplicantAdditionalLanguage.objects
                .filter(
                    talent_id=OuterRef("id"),
                    language__in=job_additional_languages,
                )
                .values("talent_id")        # group by applicant
                .annotate(count=Count("id"))  # count matches
                .values("count")[:1]        # return the count
        ),
        job_additional_language_count=Value(
            job_post.job.additional_languages.count(),
            output_field=IntegerField(),
        ),
        additional_language_score = Case(
            When(job_additional_language_count=0, then=Value(6.67)),
            default=ExpressionWrapper((F("matching_additional_languages") * Value(6.67)) / F("job_additional_language_count"), output_field=FloatField()),

        )
    ).annotate(
        matching_compulsory_additional_languages=Count("additional_languages", filter=Q(additional_languages__id__in=job_additional_languages)),
        missing_compulsory_secondary_language=Case(
            When(matching_compulsory_additional_languages__lt=len(job_additional_languages), then=Value(True)),
            output_field=BooleanField(),
            default=Value(False)
        )
    ).annotate(
        available_days_count=Subquery(
            AvailableDay.objects
                .filter(job_id=job_post.job_id)
                .values("job_id")             # group by job
                .annotate(count=Count("id"))  # count rows
                .values("count")[:1]          # return the count
        ),
        matching_days_count=Coalesce(Subquery(
            TalentAvailableDay.objects.filter(
                talent_id=OuterRef("id")
            )
            .annotate(
                day_match_exists=Exists(
                    AvailableDay.objects.filter(
                        job=job_post.job,
                        day=OuterRef("day"),
                        utc_start_time__gte=OuterRef("utc_start_time"),
                        utc_end_time__lte=OuterRef("utc_end_time"),
                    )
                )
            )
            .filter(day_match_exists=True)
            .values("talent")               # group by talent
            .annotate(cnt=Count("id"))      # count matching days
            .values("cnt")[:1]             # only return the count colum
        ), Value(0), output_field=IntegerField()),
        work_schedule_score=Case(
            When(available_days_count=None, then=Value(6.67)),
            default=(F("matching_days_count") * Value(6.67)) /F("available_days_count") ,
            output_field=FloatField()
        )
    ).annotate(
        job_flexible_availability=Value(job_post.job.flexible_availability, output_field=BooleanField()),
        final_work_schedule_score=Case(
            When(Q(flexible_availability=True) | Q(job_flexible_availability=True), then=Value(6.67)),
            default=F("work_schedule_score"),
            output_field=FloatField(),
        )
    ).annotate(
        requires_work_schedule=Exists(required_attribute_subquery.filter(working_hours=True)),
        missing_work_schedule=Case(
            When(Q(requires_work_schedule=True) & Q(work_schedule_score__lt=6.67), then=Value(True)),
            output_field=BooleanField(),
            default=Value(False)
        )
    ).annotate(
        requires_location=Exists(required_attribute_subquery.filter(location=True)),
        location_score=Case(
            When(country=job_post.country, then=Value(6.67)),
            default=Value(0.0),
            output_field=FloatField()
        )
    ).annotate(
        computed_match_score=Case(
            When(Q(requires_location=True) & Q(location_score=0.0), then=Value(0.0)),
            When(missing_compulsory_secondary_language=True, then=Value(0.0)),
            When(Q(requires_role=True) & Q(matching_role=False), then=Value(0.0)),
            When(Q(missing_required_skill=True), then=Value(0.0)),
            When(Q(requires_job_level=True) & Q(has_matching_experience=False), then=Value(0.0)),
            When(Q(requires_experience=True) & Q(meets_experience=False), then=Value(0.0)),
            When(Q(requires_minimum_education=True) & Q(has_minimum_education_requirement=False), then=Value(0.0)),
            When(Q(requires_work_structure=True) & Q(work_structure_match=False), then=Value(0.0)),
            When(Q(requires_tech_requirements=True) & Q(meets_tech_requirements=False), then=Value(0.0)),
            When(Q(missing_work_schedule=True), then=Value(0.0)),
            When(Q(missing_required_business_model=True), then=Value(0.0)),
            default=
            Coalesce(Cast(F("role_score"), FloatField()), 0.0) +
            Coalesce(Cast(F("tools_platform_score"), FloatField()), 0.0) +
            Coalesce(Cast(F("methodologies_score"), FloatField()), 0.0) +
            Coalesce(Cast(F("general_skill_score"), FloatField()), 0.0) +
            Coalesce(Cast(F("job_level_score"), FloatField()), 0.0) +
            Coalesce(Cast(F("experience_score"), FloatField()), 0.0) +
            Coalesce(Cast(F("business_model_score"), FloatField()), 0.0) +
            Coalesce(Cast(F("minimum_education_score"), FloatField()), 0.0) +
            Coalesce(Cast(F("work_structure_score"), FloatField()), 0.0) +
            Coalesce(Cast(F("tech_requirement_score"), FloatField()), 0.0) +
            Coalesce(Cast(F("first_language_score"), FloatField()), 0.0) +
            Coalesce(Cast(F("additional_language_score"), FloatField()), 0.0) +
            Coalesce(Cast(F("final_work_schedule_score"), FloatField()), 0.0) +
            Coalesce(Cast(F("location_score"), FloatField()), 0.0)
            ,
            output_field=FloatField(),
        )
    )

    return queryset