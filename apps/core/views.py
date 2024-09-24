from typing import List

from ninja.router import Router
from ninja.pagination import paginate

from core.models import Currency, Language
from core.schemas import CurrencySchema, LanguageSchema


# Create your views here.
router = Router(tags=["core"])

@router.get("currencies", response=List[CurrencySchema], tags=["Common"])
def currency_list(request):
    return Currency.objects.all()

@router.get("languages", response=List[LanguageSchema], tags=["Common"])
def language_list(request):
    return Language.objects.all()
