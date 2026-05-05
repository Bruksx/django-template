from ninja import NinjaAPI

from apps.core.renderers import ORJSONRenderer, XMLRenderer

api = NinjaAPI(docs_url="docs_1840gtc_c6403omdxnc", renderer=ORJSONRenderer())
xml_api = NinjaAPI(docs_url="docs_1840gtc_xml", renderer=XMLRenderer(), urls_namespace="xml-api")
api.add_router("auth/", "auth.views.router")
api.add_router("accounts/talents/", "accounts.views.talent.router")
api.add_router("accounts/business/", "accounts.views.business.router")
api.add_router("accounts/admin/", "accounts.views.admin.router")
api.add_router("accounts/", "accounts.views.common.router")
api.add_router("business/jobs/", "jobs.business_views.router")
api.add_router("notifications/", "notification.views.router")
api.add_router("/", "settings.views.router")
api.add_router("jobs/", "jobs.views.router")
api.add_router("core/", "core.views.router")
api.add_router("chats/", "chats.views.router")
xml_api.add_router("external-jobs/", "jobs.external_views.router")