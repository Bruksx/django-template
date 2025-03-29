import os

import django

os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'config.settings')
django.setup()
from database_seeder import delete_useless_workflows, assign_name_to_email_templates

delete_useless_workflows()
assign_name_to_email_templates()