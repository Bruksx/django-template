import os

import django


os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'config.settings')
django.setup()

from database_seeder import generate_data_for_account

generate_data_for_account(email="emilyph@1840andco.com", job_amount=5, silent=False)
