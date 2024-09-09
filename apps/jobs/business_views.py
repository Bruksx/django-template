from ninja import Router
from .schemas import EmploymentTypeSchema, CreateJobSchema
from .models import EmploymentType


router = Router(tags=["Business Jobs"])

@router.get("employment-types", response=list[EmploymentTypeSchema])
def get_employment_types(request):
    employment_types = EmploymentType.objects.filter(parent=None)
    return employment_types


@router.post("create", response=CreateJobSchema)
def create_job(request, data:CreateJobSchema):
    return CreateJobSchema