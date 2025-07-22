from django.db.models.query import QuerySet
from accounts.models import Talent, SkillCategory, Experience, Education
from .models import JobPost, RequiredAttribute
from django.db.models import (
    OuterRef, Exists, Case, When, Value, FloatField, Q, F, ExpressionWrapper, Count, Subquery, IntegerField
)
from django.db.models.expressions import RawSQL
from django.db.models.functions import Coalesce


def add_job_post_annotations(queryset: QuerySet[JobPost], talent: Talent) -> QuerySet[JobPost]:

    talent_business_models = talent.business_models.all()
    talent_skill_ids = list(talent.skills.values_list("id", flat=True))
    skills_tuple_str = f"({','.join(str(sid) for sid in talent_skill_ids)})" if talent_skill_ids else "(NULL)"
    additional_languagues_tuple_str = str(tuple(talent.additional_languages.values_list('id', flat=True)))  if talent.additional_languages.count() else "(NULL)"
    tools_platform_id = SkillCategory.objects.filter(name="Tools/Platforms").first().id
    methodologies_id = SkillCategory.objects.filter(name="Common Methodologies/Frameworks").first().id
    general_skills_id = SkillCategory.objects.filter(name="General Skills").first().id
    talent_business_model_ids = f"({','.join(str(i.id)  for i in talent_business_models)})" if talent_business_models else "(NULL)"

    required_attribute_subquery = RequiredAttribute.objects.filter(
        job=OuterRef("job")
    )

    queryset = queryset.annotate(
        requires_role=Exists(
            required_attribute_subquery.filter(role__isnull=False)
        ),
        role_score=Case(
            When(
                Q(requires_role=True) & Q(job__role=talent.role),
                then=Value(6.67)
            ),
            When(
                Q(requires_role=True) & ~Q(job__role=talent.role),
                then=Value(0.0)
            ),
            default=Value(6.67),
            output_field=FloatField()
        )
    ).annotate(
        tools_platform_score=RawSQL(f"""
            SELECT
                CASE
                    WHEN COUNT(*) FILTER (WHERE skill.category_id = '{tools_platform_id}') = 0 THEN 6.67
                    ELSE 6.67 * 
                        COUNT(*) FILTER (
                            WHERE skill.category_id = '{tools_platform_id}' AND skill.id IN {skills_tuple_str}
                        ) 
                        / 
                        NULLIF(COUNT(*) FILTER (WHERE skill.category_id = '{tools_platform_id}'), 0)
                END
            FROM jobs_job_skills as job_skills
            JOIN accounts_skill skill ON job_skills.skill_id = skill.id
            LIMIT 1
        """, [])
    ).annotate(
        methodologies_score=RawSQL(f"""
            SELECT
                CASE
                    WHEN COUNT(*) FILTER (WHERE skill.category_id = '{methodologies_id}') = 0 THEN 6.67
                    ELSE 6.67 * 
                        COUNT(*) FILTER (
                            WHERE skill.category_id = '{methodologies_id}' AND skill.id IN {skills_tuple_str}
                        ) 
                        / 
                        NULLIF(COUNT(*) FILTER (WHERE skill.category_id = '{methodologies_id}'), 0)
                END
            FROM jobs_job_skills as job_skills
            JOIN accounts_skill skill ON job_skills.skill_id = skill.id
            LIMIT 1
        """, [])
    ).annotate(
        general_skill_score=RawSQL(f"""
            SELECT
                CASE
                    WHEN COUNT(*) FILTER (WHERE skill.category_id = '{general_skills_id}') = 0 THEN 6.67
                    ELSE 6.67 * 
                        COUNT(*) FILTER (
                            WHERE skill.category_id = '{general_skills_id}' AND skill.id IN {skills_tuple_str}
                        ) 
                        / 
                        NULLIF(COUNT(*) FILTER (WHERE skill.category_id = '{general_skills_id}'), 0)
                END
            FROM jobs_job_skills as job_skills
            JOIN accounts_skill skill ON job_skills.skill_id = skill.id
            JOIN jobs_job job ON job_skills.job_id = job.id
            JOIN jobs_requiredattribute required_a ON job.id = required_a.job_id
            JOIN jobs_requiredattribute_skills requiredattribute_skills ON required_a.id = requiredattribute_skills.requiredattribute_id 
            LIMIT 1
        """, [])
    ).annotate(
        required_attribute_skill_counts=Coalesce(
            Subquery((
                RequiredAttribute.skills.through.objects
                .filter(requiredattribute__job=OuterRef("pk"))
                .values("requiredattribute__job")  # Group by job to make aggregation valid
                .annotate(skill_count=Count("skill_id"))
                .values("skill_count")[:1]
            ), output_field=IntegerField()), Value(0)),
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
                Q(requires_job_level=True) & Q(has_matching_experience=True),
                then=Value(6.67)
            ),
            When(
                Q(requires_job_level=True) & Q(has_matching_experience=False),
                then=Value(0.0)
            ),
            When(
                Q(requires_job_level=False),
                then=Value(6.67)
            ),
            default=Value(0.0),
            output_field=FloatField()
        )
    ).annotate(
        requires_experience=Exists(
        required_attribute_subquery.filter(years_of_experience=True)
    ),
        experience_score=Case(
            When(requires_experience=False, then=Value(6.67)),
            When(
                Q(requires_experience=True) & Q(job__years_of_experience__lte=talent.years_of_experience), 
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
            Education.objects.filter(level=OuterRef("job__minimum_education_level"))
        ),
        minimum_education_score=Case(
            When(requires_minimum_education=False, then=Value(6.67)),
            When(
                Q(requires_minimum_education=True) & Q(has_minimum_education_requirement=True),
                then=Value(6.67)
            ),
            default=Value(0.0),
            output_field=FloatField()
        )
    ).annotate(
        requires_work_structure=Exists(
            required_attribute_subquery.filter(work_structure=True)
        ),
        work_structure_score=Case(
            When(requires_work_structure=False, then=6.67),
            When(
                Q(requires_work_structure=True) & Q(job__work_structure=talent.work_model),
                then=Value(6.67)
            ),
            default=Value(0.0),
            output_field=FloatField()
        )
    ).annotate(
        requires_tech_requirements=Exists(
            required_attribute_subquery.filter(technological_requirement=True)
        ),
        tech_requirement_score=Case(
            When(requires_tech_requirements=False, then=6.67),
            When(
                Q(requires_tech_requirements=True) & Q(job__technological_requirement="not yet determined"),
                then=Value(6.67)
            ),
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
        work_schedule_score=RawSQL(f"""
            SELECT 
                CASE 
                    WHEN NOT EXISTS (
                        SELECT 1 FROM jobs_requiredattribute ra 
                        WHERE ra.job_id = jobs_job.id AND ra.working_hours IS NOT NULL
                    ) THEN 6.67
                    WHEN COUNT(job_av.id) = 0 THEN 0.0
                    ELSE 6.67 * (
                        SELECT COUNT(*) 
                        FROM jobs_availableday job_av2
                        JOIN accounts_talentavailableday ta ON 
                            job_av2.day = ta.day 
                            AND job_av2.start_time >= ta.start_time 
                            AND job_av2.end_time <= ta.end_time 
                        WHERE job_av2.job_id = jobs_job.id
                        AND ta.talent_id = {talent.id}
                    ) / COUNT(job_av.id)
                END
            FROM jobs_availableday job_av
            WHERE job_av.job_id = jobs_job.id
            """, [])
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
        computed_match_score=ExpressionWrapper(
            F("role_score") + F("tools_platform_score") + F("methodologies_score") +
            F("general_skill_score") + F("job_level_score") + F("experience_score") +
            F("business_model_score") + F("minimum_education_score") + F("work_structure_score") +
            F("tech_requirement_score") + F("first_language_score") + F("additional_language_score") +
            F("work_schedule_score") + F("location_score"),
            output_field=FloatField()
        )
    )
    return queryset