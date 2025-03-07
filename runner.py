import os
from random import choice

import django


os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'config.settings')
django.setup()
from database_seeder import update_talent_applications_to_no_stage

# generate_data("P455@1840GTC", ["ohaegbulouis@gmail.com"])

update_talent_applications_to_no_stage()