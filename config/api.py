from ninja import NinjaAPI
from apps.core.renderers import ORJSONRenderer


api = NinjaAPI(docs_url="docs_1840gtc_c6403omdxnc", renderer=ORJSONRenderer())

api.add_router("auth/", "auth.views.router")
api.add_router("accounts/", "accounts.views.router")
api.add_router("accounts/business/", "accounts.business_views.router")