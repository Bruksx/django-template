from pathlib import Path
from typing import List
from uuid import UUID

from django.db.models import Q
from django.http import FileResponse
from ninja.errors import HttpError
from ninja.router import Router

from core.models import Currency, Language, State, City
from core.schemas import CurrencySchema, LanguageSchema, GenericNameAndUidSchema


# Create your views here.
router = Router(tags=["core"])
root_router = Router()

@router.get("currencies", response=List[CurrencySchema], tags=["Common"])
def currency_list(request, search=""):
    queryset = Currency.objects.all()
    if search:
        queryset = queryset.filter(Q(name__icontains=search)|Q(abbreviation__icontains=search))
    return queryset.order_by("abbreviation")

@router.get("languages", response=List[LanguageSchema], tags=["Common"])
def language_list(request, search=""):
    queryset = Language.objects.all()
    if search:
        queryset = queryset.filter(name__icontains=search)
    return queryset.distinct("name").order_by("name")


@router.get("states", response=List[GenericNameAndUidSchema], tags=["Common"])
def state_list(request, country:UUID, search=""):
    queryset = State.objects.filter(country__uid=country)
    if search:
        queryset = queryset.filter(name__icontains=search)
    return queryset.distinct("name").order_by("name")



@router.get("cities", response=List[GenericNameAndUidSchema], tags=["Common"])
def city_list(request,  state:UUID, search=""):
    queryset = City.objects.filter(state__uid=state)
    if search:
        queryset = queryset.filter(name__icontains=search)
    return queryset.distinct("name").order_by("name")


@root_router.get("{filename}")
def get_well_known(request, filename:str):
    base_dir = Path(__file__).resolve().parent.parent.parent / "well_known"
    file_path = base_dir / filename

    if not file_path.exists():
        raise HttpError(404, "File not found")

    content_type = "application/json" if filename.endswith(".json") else "text/plain"
    return FileResponse(open(file_path, "rb"), content_type=content_type)
