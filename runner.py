import os
from random import choice

import django


os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'config.settings')
django.setup()
from database_seeder import create_job_posts

create_job_posts()
