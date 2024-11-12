from typing import List

from helpers.email.utils import send_email, render_html_email


def send_shared_job_email(job_post, emails: List[str]=None, lang="en"):
    if not emails:
        return
    html = f'jobs/{lang}/share_job.html'
    context = {
        'talent': "User",
        'job_title': job_post.job.title
    }
    html_content  = render_html_email(html, context)
    send_email(subject='Shared Job Post', emails=emails, html_body=html_content)