from typing import List

from config import settings
from helpers.email.utils import send_email, render_html_email


def send_invite_to_apply_email(job_post, emails: List[str]=None, lang="en"):
	if not emails:
		return
	if not job_post.job.get_title:
		return
	html = f'jobs/{lang}/invite.html'
	frontend_job_url = f"{settings.FRONTEND_URL}jobs-listing"
	context = {
		'link': f"{frontend_job_url}/{job_post.uid}",
		'role': job_post.job.get_title,
		"verb": 'an' if job_post.job.get_title[0] in ['a', 'e', 'i', 'o', 'u'] else 'a'
	}
	html_content  = render_html_email(html, context)
	send_email(subject='Invitation to Apply', emails=emails, html_body=html_content)

def send_indeed_apply_email(job_post, email, first_name, last_name, lang="en"):
	if not job_post.job.get_title:
		return
	html = f'jobs/{lang}/indeed_apply.html'
	frontend_job_url = f"{settings.FRONTEND_URL}jobs-listing"
	role = job_post.job.get_title
	context = {
		'link': f"{frontend_job_url}/{job_post.uid}",
		'role': role,
		"verb": 'an' if job_post.job.get_title[0] in ['a', 'e', 'i', 'o', 'u'] else 'a',
		'talent': f"{first_name} {last_name}"
	}
	html_content  = render_html_email(html, context)
	send_email(subject=f'1840 GTC: Apply to the {role} position', emails=[email], html_body=html_content)


def send_shared_job_email(job_post, emails: List[str]=None, lang="en"):
	if not emails:
		return
	html = f'jobs/{lang}/share_job.html'
	frontend_job_url = f"{settings.FRONTEND_URL}jobs-listing"
	context = {
		'talent': "User",
		'company_logo': job_post.job.logo_url(),
		'job_link': f"{frontend_job_url}/{job_post.uid}",
		'job_title': job_post.job.get_title,
		'company': job_post.job.hiring_company(),
		'location': job_post.get_location(),
		"structure": job_post.job.get_work_structure()
	}
	html_content  = render_html_email(html, context)
	send_email(subject='Shared Job Post', emails=emails, html_body=html_content)
