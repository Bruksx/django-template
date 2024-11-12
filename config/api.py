from ninja import NinjaAPI
from apps.core.renderers import ORJSONRenderer
from ninja.pagination import PageNumberPagination


api = NinjaAPI(docs_url="docs_1840gtc_c6403omdxnc", renderer=ORJSONRenderer())

api.add_router("auth/", "auth.views.router")
api.add_router("accounts/talents/", "accounts.views.talent.router")
api.add_router("accounts/business/", "accounts.views.business.router")
api.add_router("accounts/", "accounts.views.common.router")
api.add_router("jobs/business/", "jobs.business_views.router")
api.add_router("jobs/", "jobs.views.router")
api.add_router("core/", "core.views.router")
api.add_router("chats/", "chats.views.router")