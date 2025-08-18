def test():
    '''.annotate(
        talent_required_skill_count=Count(TalentSkill.objects.filter(
            talent_id=OuterRef("applicant__id"), skill_id__in=required_skill_ids
            )),
        missing_required_skill=Case(
            When(
                Q(talent_required_skill_count__lt=required_skill_count),
                then=Value(True)
            ),
            default=Value(False),
            output_field=BooleanField()
        )
    ).annotate(
        gen_skill_count=Count("job_post__job__skills", filter=Q(job_post__job__skills__category_id=general_skills_id)),
        gen_skill_intercept_count=Count("applicant__skills", filter=Q(
            applicant__skills__category_id=general_skills_id, applicant__skills__in=job_general_skills
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
        tools_platform_count=Count("job_post__job__skills", filter=Q(job_post__job__skills__category_id=tools_platform_id)),
        tools_platform_intercept_count=Count("applicant__skills", filter=Q(
            applicant__skills__category_id=tools_platform_id, applicant__skills__in=job_tools_skills
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
        methodologies_count=Count("job_post__job__skills", filter=Q(job_post__job__skills__category_id=tools_platform_id)),
        methodologies_intercept_count=Count("applicant__skills", filter=Q(
            applicant__skills__category_id=general_skills_id, applicant__skills__in=job_methodology_skills
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
        business_model_score=Value(6.67)
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
            Education.objects.filter(talent=OuterRef("applicant"), level__order__gte=OuterRef("job_post__job__minimum_education_level"))
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
        job_addtional_language_count=Count("job_post__job__additional_languages"),
        matching_additional_languages=Count("applicant__additional_languages", filter=Q(applicant__additional_languages__in=job_additional_languages)),
        additional_language_score=Case(
            When(job_addtional_language_count=0, then=6.67),
            default=ExpressionWrapper(
                (F("matching_additional_languages") / F("job_addtional_language_count")) * 6.67,
                output_field=FloatField()
            ),
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
        available_days_count=Count("job_post__job__availableday"),
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
            When(available_days_count=0, then=Value(6.67)),
            default=ExpressionWrapper(
                (F("matching_days_count")/F("available_days_count")) * Value(6.67),
                output_field=FloatField()
            ),
            output_field=FloatField()
        )
    ).annotate(
        final_work_schedule_score=Case(
            When(Q(applicant__flexible_availability=True) | Q(job_post__job__flexible_availability=True), then=Value(6.67)),
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
            When(job_post__country=F("applicant__country"), then=Value(6.67)),
            default=Value(0.0),
            output_field=FloatField()
        )
    ).annotate(
        computed_match_score=Case(
            When(Q(requires_location=True) & ~Q(job_post__country=F("applicant__country")), then=Value(0.0)),
            When(missing_compulsory_secondary_language=True, then=Value(0.0)),
            When(Q(requires_role=True) & Q(matching_role=False), then=Value(0.0)),
            When(Q(missing_required_skill=True), then=Value(0.0)),
            When(Q(requires_job_level=True) & Q(has_matching_experience=False), then=Value(0.0)),
            When(Q(requires_experience=True) & Q(meets_experience=False), then=Value(0.0)),
            When(Q(requires_minimum_education=True) & Q(has_minimum_education_requirement=False), then=Value(0.0)),
            When(Q(requires_work_structure=True) & Q(work_structure_match=False), then=Value(0.0)),
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
    )'''
