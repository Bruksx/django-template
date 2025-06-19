from typing import List

from django.db.models import Q
from ninja.router import Router

from core.models import Currency, Language
from core.schemas import CurrencySchema, LanguageSchema

# Create your views here.
router = Router(tags=["core"])

@router.get("currencies", response=List[CurrencySchema], tags=["Common"])
def currency_list(request, search=""):
    queryset = Currency.objects.all()
    if search:
        queryset = queryset.filter(Q(name__icontains=search)|Q(abbreviation__icontains=search))
    return queryset.distinct("abbreviation").order_by("abbreviation")

@router.get("languages", response=List[LanguageSchema], tags=["Common"])
def language_list(request, search=""):
    queryset = Language.objects.all()
    if search:
        queryset = queryset.filter(name__icontains=search)
    return queryset.distinct("name").order_by("name")
