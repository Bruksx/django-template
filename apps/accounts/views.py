from uuid import UUID

from django.core.mail import send_mail
from django.db import transaction
from ninja.responses import Response

from helpers.images import convert_base64_to_image_file
from ninja import Router
from ninja.errors import HttpError
from ninja_jwt.authentication import JWTAuth

from accounts.enums import UserType, AuthType
from accounts.models import Talent
from accounts.models import User, VerificationCode, Education, TalentSkill, Experience, TalentAvailability, \
    Skill
from accounts.schemas import common as common_schemas
from accounts.schemas import talent as talent_schemas
from core.models import Language

router = Router(tags=["Account"])


@router.post("create-account/")
def create_account(request, data: common_schemas.RegisterSchema):
    existing_user = User.objects.filter(email=data.email).exists()
    if existing_user:
        raise HttpError(400, "An account with this email already exists")
    verification_code = VerificationCode(email=data.email)
    raw_code = verification_code.save()
    send_mail(
        "OTP",
        f"{raw_code}",
        "from@example.com",
        [data.email],
        fail_silently=False,
    )
    return {
        "message": "verification mail sent!"
    }


@router.post("validate-otp", response={200:talent_schemas.LoggedInUserSchema})
@transaction.atomic
def validate_otp(request, data: talent_schemas.ValidateTalentOTPSchema):
    existing_user = User.objects.filter(email=data.email).exists()
    if existing_user:
        raise HttpError(400, "An account with this email already exists")
    verification_code = VerificationCode.objects.filter(email=data.email).last()
    if not verification_code:
        raise HttpError(400, "Incorrect otp")
    is_correct = verification_code.verify_code(data.otp)
    if not is_correct:
        raise HttpError(400, "This OTP is invalid")
    user = User.objects.create_user(first_name=data.first_name,
                                    last_name=data.last_name,
                                    email=data.email,
                                    password=data.password,
                                    username=None,
                                    phone_number=data.phone_number,
                                    auth_mode=AuthType.EMAIL.value,
                               type=UserType.TALENT.value,
                               email_verified=True, is_active=True)
    Talent.objects.create(
        user=user,
        country=data.country,
        preferred_communication=data.preferred_communication.value,
        state=data.state,
        city=data.city,
        postal_code=data.postal_code
    )
    return user



@router.post("complete-profile/first_step",
             response=talent_schemas.UserSchema,
             auth=JWTAuth())
@transaction.atomic
def complete_talent_profile(request, data: talent_schemas.CompleteTalentProfileSchema):
    talent_user = Talent.objects.filter(user=request.user).first()
    if not talent_user:
        raise HttpError(403, "Not allowed")
    request_data = data.__dict__
    if "gender" in request_data:
        talent_user.user.update(gender=request_data.pop("gender").value)
    if "availability" in request_data:
        if hasattr(talent_user,"talentavailability"):
            talent_user.availability.update(**request_data.pop("availability").__dict__)
        else:
            TalentAvailability.objects.create(**request_data.pop("availability").__dict__, talent=talent_user)
    if request_data.get("photo"):
        request_data["photo"] = convert_base64_to_image_file(request_data["photo"])
    talent_user.update(**request_data)
    return talent_user.user


@router.post("complete-profile/next_step", response=talent_schemas.UserSchema, auth=JWTAuth())
@transaction.atomic
def complete_talent_profile2(request, data: talent_schemas.CompleteTalentProfileSchema2):
    talent_user = Talent.objects.filter(user=request.user).first()
    if not talent_user:
        raise HttpError(403, "Not allowed")
    request_data = data.__dict__
    education_history = request_data.pop("education_history", list())
    for education in education_history:
        edu_data = education.__dict__
        edu_uid = edu_data.pop("uid", None)
        if edu_uid:
            Education.objects.filter(uid=edu_uid, talent=talent_user).update(**edu_data)
        else:
            Education(**edu_data, talent=talent_user).save()
    additional_languages = request_data.pop("additional_languages", list())
    talent_user.update(**request_data)
    talent_user.additional_languages.add(*additional_languages)
    return talent_user.user


@router.post("complete-profile/last_step", response=talent_schemas.UserSchema, auth=JWTAuth())
@transaction.atomic
def complete_talent_profile3(request, data: talent_schemas.CompleteTalentProfileSchema3):
    talent_user = Talent.objects.filter(user=request.user).first()
    if not talent_user:
        raise HttpError(403, "Not allowed")
    if data.skill:
        skill_data = data.skill.__dict__
        tools = skill_data.pop("tools")
        frameworks = skill_data.pop("frameworks")
        business_models = skill_data.pop("business_models")
        general = skill_data.pop("general_skills")
        soft = skill_data.pop("soft_skills")
        TalentSkill.objects.create(talent=talent_user, **skill_data)
        talent_user.talentskill.soft_skills.set(soft)
        talent_user.talentskill.general_skills.set(general)
        talent_user.talentskill.business_models.set(business_models)
        talent_user.talentskill.frameworks.set(frameworks)
        talent_user.talentskill.tools.set(tools)
    for experience in data.experience_history:
        experience_data = experience.__dict__
        experience_uid = experience_data.pop("uid", None)
        if experience_uid:
            Experience.objects.filter(uid=experience_uid).update(**experience_data)
        else:
            Experience(**experience_data, talent=talent_user).save()
    return talent_user.user

@router.get("talent-profile", response=talent_schemas.TalentUserSchema, auth=JWTAuth())
def talent_profile(request):
    talent_user = Talent.objects.filter(user=request.user).first()
    if not talent_user:
        raise HttpError(403, "Not allowed")
    return talent_user

@router.patch("talent-profile", response=talent_schemas.UserSchema, auth=JWTAuth())
def update_talent_profile(request, data: talent_schemas.UpdateTalentProfileSchema):
    talent_user = Talent.objects.filter(user=request.user).first()
    if not talent_user:
        raise HttpError(403, "Not allowed")
    talent_user.user.update(first_name=data.first_name,
                                    last_name=data.last_name,
                                    phone_number=data.phone_number)
    talent_user = talent_user.update(
        country=data.country,
        preferred_communication=data.preferred_communication.value,
        state=data.state,
        city=data.city,
        postal_code=data.postal_code
    )
    return talent_user.user

@router.delete("talent/education/{education_uid}",
               response={204: None},
               auth=JWTAuth())
def delete_talent_education(request, education_uid:UUID):
    talent_user = Talent.objects.filter(user=request.user).first()
    if not talent_user:
        raise HttpError(403, "Not allowed")
    education = talent_user.education_set.filter(uid=education_uid).first()
    if not education:
        raise HttpError(404, "This education does not exist")
    education.delete()
    return Response(status=204, data=None)


@router.delete("talent/experience/{experience_uid}",
               response={204: None}, auth=JWTAuth())
def delete_talent_experience(request, experience_uid:UUID):
    talent_user = Talent.objects.filter(user=request.user).first()
    if not talent_user:
        raise HttpError(403, "Not allowed")
    experience = talent_user.experience_set.filter(uid=experience_uid).first()
    if not experience:
        raise HttpError(404, "This experience does not exist")
    experience.delete()
    return Response(status=204, data=None)

