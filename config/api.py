from ninja import NinjaAPI

api = NinjaAPI(docs_url="docs_1840gtc_c6403omdxnc")

api.add_router("accounts/", "accounts.views.router")