from ninja.router import Router
from jobs.models import EmploymentType

# Create your views here.
router = Router()

@router.get("hello-world")
def hello_world(request):
    parent = EmploymentType.objects.first()
    uid = parent.uid
    new_type = EmploymentType(
        parent = uid,
        name = "new"
    )
    
    return {}