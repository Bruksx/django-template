from django.contrib import admin
from .models import Currency, GTCSettings

# Register your models here.
admin.site.register(Currency)
admin.site.register(GTCSettings)