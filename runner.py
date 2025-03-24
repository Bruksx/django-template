import os
from random import choice

import django


os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'config.settings')
django.setup()
from database_seeder import create_job_posts, update_job_post_status

create_job_posts()
update_job_post_status()