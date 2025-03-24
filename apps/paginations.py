from collections import OrderedDict
from typing import Optional, Any

from django.core.paginator import Page, InvalidPage
from django.db.models import QuerySet
from django.http import HttpRequest
from ninja import Schema
from ninja.types import DictStrAny
from ninja_extra.exceptions import NotFound
from ninja_extra.pagination import PageNumberPaginationExtra
from pydantic import Field


class CustomPageNumberPaginationExtra(PageNumberPaginationExtra):

    class Input(Schema):
        page: int = Field(1, gt=0)
        page_size: int = Field(100, lt=200)

    def get_paginated_response(self, base_url: str, page: Page, **kwargs) -> DictStrAny:
        added_fields = [(key, kwargs[key]) for key in kwargs]
        return OrderedDict(
            [
                ('count', page.paginator.count),
                ("next_page", page.next_page_number()),
                ("previous_page", page.previous_page_number()),
                ("next", self.get_next_link(base_url, page=page)),
                ("previous", self.get_previous_link(base_url, page=page)),
                ("results", list(page)),
                *added_fields
            ]
        )

    def paginate_queryset(
        self,
        queryset: QuerySet,
        pagination: Input,
        request: Optional[HttpRequest] = None,
        **params: DictStrAny,
    ) -> Any:
        assert request, "request is required"
        current_page_number = pagination.page
        paginator = self.paginator_class(queryset, pagination.page_size)
        try:
            url = request.build_absolute_uri()
            page: Page = paginator.page(current_page_number)
            return self.get_paginated_response(base_url=url, page=page, **params)
        except InvalidPage as exc:  # pragma: no cover
            msg = "Invalid page. {page_number} {message}".format(
                page_number=current_page_number, message=str(exc)
            )
            raise NotFound(msg) from exc