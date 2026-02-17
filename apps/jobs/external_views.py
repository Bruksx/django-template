from django.http import StreamingHttpResponse
from ninja import Router

from services.job_posting.linkedin_xml_generator import generate_job_post_xml_stream
from services.job_posting.schema.indeed_xml import Source

router = Router()




@router.get("job-posts/linkedin-pool.xml", summary="fetch job posts for linkedin in xml format",
            tags=["Job Posts"])
def get_linkedin_job_posts_xml_pool(request, *args, **kwargs):
    return StreamingHttpResponse(generate_job_post_xml_stream(), content_type="application/xml")

@router.get("job-posts/linkedin-pool-staffing.xml", summary="fetch staffing job posts for linkedin in xml format",
            tags=["Job Posts"])
def get_linkedin_staffing_job_posts_xml_pool(request, *args, **kwargs):
    return StreamingHttpResponse(generate_job_post_xml_stream(staffing=True), content_type="application/xml")


@router.get("job-posts/indeed-pool.xml", summary="fetch job posts for linkedin in xml format",
            tags=["Job Posts"])
def get_indeed_job_posts_xml_pool(request, *args, **kwargs):
    page = request.GET.get("page")
    page_size = request.GET.get("page-size")
    return StreamingHttpResponse(Source.to_xml_stream(page, page_size), content_type="application/xml")


