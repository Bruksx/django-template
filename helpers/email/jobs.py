from typing import List

from config import settings
from helpers.email.utils import send_email, render_html_email


def send_shared_job_email(job_post, emails: List[str]=None, lang="en"):
    if not emails:
        return
    html = f'jobs/{lang}/share_job.html'
    #TODO: add frontend job url
    frontend_job_url = f"{settings.FRONTEND_URL}/jobs/"
    context = {
        'talent': "User",
        'company_logo': job_post.job.logo_url(),
        'job_link': f"{frontend_job_url}/{job_post.job.uid}",
        'job_title': job_post.job.title,
        'company': job_post.job.hiring_company(),
        'location': job_post.country.name,
        "structure": job_post.job.work_structure
    }
    html_content  = render_html_email(html, context)
    send_email(subject='Shared Job Post', emails=emails, html_body=html_content)