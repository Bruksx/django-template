from typing import List

from django.template import loader

from helpers.email.utils import send_email


def send_shared_job_email(job_post, emails: List[str]=None, lang="en"):
    template = loader.get_template(f'jobs/{lang}/share_job.html')
    if not emails:
        return
    context = {
        'talent': "User",
        'job_title': job_post.job.title
    }
    html_content = template.render(context)
    send_email(subject='Shared Job Post', emails=emails, html_body=html_content)