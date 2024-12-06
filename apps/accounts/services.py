from django.http import HttpResponse
from django.shortcuts import render

import settings
from accounts.schemas.talent import TalentUserSchema
from helpers.utils import convert_base64_to_image_file, html_to_pdf

def download_talent_cv(request, talent):
    cv_data = TalentUserSchema.from_orm(talent).dict()
    cv_data["image_url"] = settings.IMAGE_URL
    cv_data["css_url"] = settings.CSS_URL
    rendered_html = render(
        request, "accounts/en/talent-cv.html",
        context=cv_data
    ).content.decode()
    #todo: design the cv html
    file_name = f"talent-cv-{talent.uid}.pdf"
    pdf_file = html_to_pdf(rendered_html)
    response = HttpResponse(pdf_file, content_type="application/pdf")
    response["Content-Disposition"] = f'attachment; filename="{file_name}"'
    return response