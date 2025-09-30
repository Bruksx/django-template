from typing import List

from config import settings
from helpers.email.utils import send_email, render_html_email


def send_invite_to_apply_email(job_post, emails: List[str]=None, lang="en"):
    if not emails:
        return
    html = f'jobs/{lang}/invite.html'
    frontend_job_url = f"{settings.FRONTEND_URL}job-details"
    context = {
        'link': f"{frontend_job_url}/{job_post.job.uid}",
        'role': job_post.job.get_title,
        "verb": 'an' if job_post.job.get_title[0] in ['a', 'e', 'i', 'o', 'u'] else 'a'
    }
    html_content  = render_html_email(html, context)
    send_email(subject='Invitation to Apply', emails=emails, html_body=html_content)


def send_shared_job_email(job_post, emails: List[str]=None, lang="en"):
    if not emails:
        return
    html = f'jobs/{lang}/share_job.html'
    frontend_job_url = f"{settings.FRONTEND_URL}/job-details/"
    context = {
        'talent': "User",
        'company_logo': job_post.job.logo_url(),
        'job_link': f"{frontend_job_url}/{job_post.job.uid}",
        'job_title': job_post.job.get_title,
        'company': job_post.job.hiring_company(),
        'location': job_post.country.name,
        "structure": job_post.job.work_structure
    }
    html_content  = render_html_email(html, context)
    send_email(subject='Shared Job Post', emails=emails, html_body=html_content)