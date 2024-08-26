from ninja import Router

router = Router()


# Create your views here.
@router.get("/hello-world")
def hello_world(request):
    return "hello world"