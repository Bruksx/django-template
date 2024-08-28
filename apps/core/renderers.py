from ninja.renderers import BaseRenderer
import orjson
import json


class ORJSONRenderer(BaseRenderer):
    media_type = "application/json"

    def render(self, request, data, *, response_status):
        message = ""
        if str(response_status)[0] != "2":
            message = format_errors(dict(data), response_status)
        custom_response = {
            "code": response_status,
            "message": message,
            "data": dict(data),
        }
        return orjson.dumps(custom_response)



def format_errors(errors, response_status):
    if response_status == 422:
        readable_errors = []
        for error in errors["detail"]:
            location = " -> ".join(error.get("loc", [])) 
            message = error.get("msg", "Unknown error")
            return f"Error in {location}: {message}"