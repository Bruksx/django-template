from django.http import StreamingHttpResponse
from ninja import Router

from services.job_posting.linkedin_xml_generator import generate_job_post_xml_stream

router = Router()




@router.get("job-posts/linkedin-pool.xml", summary="fetch job posts for linkedin in xml format",
            tags=["Job Posts"])
def get_linkedin_job_posts_xml_pool(request, *args, **kwargs):
    return StreamingHttpResponse(generate_job_post_xml_stream(), content_type="application/xml")
