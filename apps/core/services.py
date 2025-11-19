from .models import GTCSettings


def get_settings():
    return GTCSettings.get_settings()[0]