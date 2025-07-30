from django.db.models.query import QuerySet
from accounts.models import Talent, SkillCategory, Experience, Education, TalentAvailableDay
from .models import JobPost, RequiredAttribute, RequiredSecondaryLanguage, RequiredSkill, AvailableDay
from django.db.models import (
    OuterRef, Exists, Case, When, Value, FloatField, Q, F, ExpressionWrapper, Count, Subquery, IntegerField, 
    BooleanField
)
from django.db.models.expressions import RawSQL
from django.db.models.functions import Coalesce, Cast


def add_job_post_annotations(queryset: QuerySet[JobPost], talent: Talent) -> QuerySet[JobPost]:

    talent_business_models = talent.business_models.all()
    talent_skill_ids = list(talent.skills.values_list("id", flat=True))
    additional_lang_ids = list(talent.additional_languages.values_list("id", flat=True))
    skills_tuple_str = f"({','.join(str(sid) for sid in talent_skill_ids)})" if talent_skill_ids else "(NULL)"
    additional_languagues_tuple_str = f"({','.join(str(aid) for aid in additional_lang_ids)})" if additional_lang_ids else "(NULL)"
    tools_platform_id = SkillCategory.objects.filter(name="Tools/Platforms").first().id
    methodologies_id = SkillCategory.objects.filter(name="Common Methodologies/Frameworks").first().id
    general_skills_id = SkillCategory.objects.filter(name="General Skills").first().id
    talent_business_model_ids = f"({','.join(str(i.id)  for i in talent_business_models)})" if talent_business_models else "(NULL)"
    talent_available_days = TalentAvailableDay.objects.filter(talent=talent)
    talent_workdays = [i.day for i in talent_available_days]

    talent_general_skills = talent.skills.filter(category__id=general_skills_id)
    talent_tools_skills = talent.skills.filter(category_id=tools_platform_id)
    talent_methodology_skills = talent.skills.filter(category_id=methodologies_id)

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
                Q(matching_role=True),
                then=Value(6.67)
            ),
            default=Value(0.0),
            output_field=FloatField()
        )
    ).annotate(
        missing_required_skill=Exists(
            RequiredSkill.objects.exclude(skill__id__in=talent_skill_ids)
        )
    ).annotate(
        gen_skill_count=Count("job__skills", filter=Q(job__skills__category_id=general_skills_id)),
        gen_skill_intercept_count=Count("job__skills", filter=Q(
            job__skills__category_id=general_skills_id, job__skills__in=talent_general_skills
        )),
        general_skill_score=Case(
            When(Q(gen_skill_count=0), then=Value(6.67)),
            default=ExpressionWrapper(
                (F("gen_skill_intercept_count") / F("gen_skill_count")) * Value(6.67),
                output_field=FloatField()
            ),
            output_field=FloatField()
        )
    ).annotate(
        tools_platform_count=Count("job__skills", filter=Q(job__skills__category_id=tools_platform_id)),
        tools_platform_intercept_count=Count("job__skills", filter=Q(
            job__skills__category_id=tools_platform_id, job__skills__in=talent_tools_skills
        )),
        tools_platform_score=Case(
            When(Q(tools_platform_count=0), then=Value(6.67)),
            default=ExpressionWrapper(
                (F("tools_platform_intercept_count") / F("tools_platform_count")) * Value(6.67),
                output_field=FloatField()
            ),
            output_field=FloatField()
        )
    ).annotate(
        methodologies_count=Count("job__skills", filter=Q(job__skills__category_id=tools_platform_id)),
        methodologies_intercept_count=Count("job__skills", filter=Q(
            job__skills__category_id=general_skills_id, job__skills__in=talent_methodology_skills
        )),
        methodologies_score=Case(
            When(Q(methodologies_count=0), then=Value(6.67)),
            default=ExpressionWrapper(
                (F("methodologies_intercept_count") / F("methodologies_count")) * Value(6.67),
                output_field=FloatField()
            ),
            output_field=FloatField()
        )
    ).annotate(
        business_model_score=RawSQL(f"""
            SELECT
                CASE
                    WHEN COUNT(ra_bms.id) = 0 THEN 6.67
                    ELSE 6.67 * 
                        COUNT(*) FILTER (
                            WHERE bm.id IN {talent_business_model_ids}
                        ) 
                        / 
                        NULLIF(COUNT(ra_bms.id) , 0)
                END
            FROM jobs_requiredattribute ra
            JOIN jobs_requiredattribute_business_models ra_bms ON ra.id = ra_bms.requiredattribute_id
            JOIN jobs_businessmodel bm ON ra_bms.businessmodel_id = bm.id
            WHERE ra.job_id = jobs_jobpost.job_id
            LIMIT  1            
        """, [])
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
            Education.objects.filter(talent=talent, level__order__gte=OuterRef("job__minimum_education_level"))
        ),
        minimum_education_score=Case(
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
                Q(requires_tech_requirements=True) & Q(job__technological_requirement="undetermined"),
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
            When(
                Q(requires_tech_requirements=True) & Q(job__first_language=talent.native_language),
                then=Value(6.67)
            ),
            default=Value(0.0),
            output_field=FloatField()
        )
    ).annotate(
        additional_language_score=RawSQL(f"""
            SELECT
                CASE
                    WHEN NOT EXISTS (
                        SELECT 1
                        FROM jobs_requiredattribute ra
                        WHERE ra.job_id = jobs_job.id AND ra.secondary_language IS NOT NULL
                    ) THEN 6.67
                    WHEN COUNT(jal.language_id) = 0 THEN 0.0
                    ELSE 6.67 * 
                        COUNT(*) FILTER (
                            WHERE jal.language_id IN {additional_languagues_tuple_str}
                        ) / 
                        NULLIF(COUNT(*), 0)
                END
            FROM jobs_job_additional_languages jal
            WHERE jal.job_id = jobs_job.id
        """, [])
    ).annotate(
        missing_compulsory_secondary_language=Exists(
            RequiredSecondaryLanguage.objects.filter(
                required_attribute__job=OuterRef("job")
            ).exclude(id__in=additional_lang_ids)
        )
    ).annotate(
        work_schedule_score=RawSQL(f"""
            SELECT 
                CASE 
                    WHEN NOT EXISTS (
                        SELECT 1 FROM jobs_requiredattribute ra 
                        WHERE ra.job_id = jobs_job.id AND ra.working_hours IS NOT NULL
                    ) THEN 6.67
                    WHEN COUNT(job_av.id) = 0 THEN 6.67
                    ELSE 6.67 * (
                        SELECT COUNT(*) 
                        FROM jobs_availableday job_av2
                        JOIN accounts_talentavailableday ta ON 
                            job_av2.day = ta.day 
                            AND job_av2.utc_start_time >= ta.utc_start_time 
                            AND job_av2.utc_end_time <= ta.utc_end_time 
                        WHERE job_av2.job_id = jobs_job.id
                        AND ta.talent_id = {talent.id}
                    ) / COUNT(job_av.id)
                END
            FROM jobs_availableday job_av
            WHERE job_av.job_id = jobs_job.id
            """, [])
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
        location_match=Exists(
            JobPost.objects.filter(job=OuterRef("job"), country=talent.country)
        ),
        location_score=Case(
            When(requires_location=False, then=Value(6.67)),
            When(Q(requires_location=True) & Q(location_match=True), then=Value(6.67)),
            default=Value(0.0),
            output_field=FloatField()
        )
    ).annotate(
        computed_match_score=Case(
            When(Q(requires_location=True) & Q(location_match=False), then=Value(0.0)),
            When(missing_compulsory_secondary_language=True, then=Value(0.0)),
            When(Q(requires_role=True) & Q(matching_role=False), then=Value(0.0)),
            When(Q(missing_required_skill=True), then=Value(0.0)),
            When(Q(requires_job_level=True) & Q(has_matching_experience=False), then=Value(0.0)),
            When(Q(requires_experience=True) & Q(meets_experience=False), then=Value(0.0)),
            When(Q(requires_minimum_education=True) & Q(has_minimum_education_requirement=False), then=Value(0.0)),
            When(Q(requires_work_structure=True) & Q(job__work_structure__in=talent.work_models), then=Value(0.0)),
            When(Q(requires_tech_requirements=True) & Q(meets_tech_requirements=False), then=Value(0.0)),
            When(Q(missing_work_schedule=True), then=Value(0.0)),
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