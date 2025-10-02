from typing import List
from uuid import UUID

from django.db.models import Q
from ninja.router import Router

from core.models import Currency, Language, State, City
from core.schemas import CurrencySchema, LanguageSchema, GenericNameAndUidSchema


# Create your views here.
router = Router(tags=["core"])

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


