from ninja.renderers import BaseRenderer
import orjson
import json
from core.schemas import FieldErrorSchema, StringDetailSchema, MessageSchema
from pydantic_core import ValidationError


class ORJSONRenderer(BaseRenderer):
    media_type = "application/json"

    def render(self, request, data, *, response_status):
        message = get_message(data, response_status)
        
        custom_response = {
            "code": response_status,
            "message": message,
            "data": format_data(data),
        }
        return orjson.dumps(custom_response)



def format_errors(data):
    for error in data["detail"]:
        location = " -> ".join(error.get("loc", [])) 
        message = error.get("msg", "Unknown error")
        return f"Error in {location}: {message}"


def format_data(data):
    return dict(data)


def get_message(data, response_status):
    try:
        FieldErrorSchema(**data)
        return format_errors(data)
    except ValidationError:
        pass
    
    try: 
        res = StringDetailSchema(**data)
        return res.detail
    except ValidationError:
        pass

    try:
        res = MessageSchema(**data)
        return res.message
    except ValidationError:
        pass
    return ""


def get_message(data, response_status):
    schemas = [FieldErrorSchema, StringDetailSchema, MessageSchema]
    for schema in schemas:
        try:
            res = schema(**data)
            # Handle the specific field based on the schema
            if hasattr(res, 'detail'):
                return res.detail
            elif hasattr(res, 'message'):
                return res.message
            elif hasattr(res, 'errors'):
                return format_errors(data)
        except ValidationError:
            continue
    return ""