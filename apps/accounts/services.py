from django.conf import settings
from django.http import HttpResponse
from django.shortcuts import render
from helpers.utils import html_to_pdf

from accounts.schemas.talent import TalentResumeSchema


def download_talent_cv(request, talent):
    cv_data = TalentResumeSchema.from_orm(talent).dict()
    asset_url = f"{settings.WEB_URL}/static/img"
    rendered_html = render(
        request, "accounts/en/talent-cv.html",
        context=dict(talent=cv_data, asset_url=asset_url)
    ).content.decode()
    file_name = f"talent-cv-{talent.uid}.pdf"
    pdf_file = html_to_pdf(rendered_html)
    response = HttpResponse(pdf_file, content_type="application/pdf")
    response["Content-Disposition"] = f'attachment; filename="{file_name}"'
    return response