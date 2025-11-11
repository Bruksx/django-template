from ninja import NinjaAPI

from apps.core.renderers import ORJSONRenderer, XMLRenderer

well_known = NinjaAPI(docs_url="well-known-doc", renderer=ORJSONRenderer(), urls_namespace="well_known")
well_known.add_router(".well-known/", "core.views.root_router")