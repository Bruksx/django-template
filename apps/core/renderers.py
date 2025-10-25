from io import StringIO

import orjson
from core.schemas import FieldErrorSchema, StringDetailSchema, MessageSchema
from django.utils.xmlutils import SimplerXMLGenerator
from ninja.renderers import BaseRenderer
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
    if isinstance(data, str):
        return data
    if isinstance(data, list):
        return data
    return dict(data)


def get_message(data, response_status):
    if isinstance(data, str):
        return data
    if isinstance(data, list):
        return ""
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



# renderers.py

class XMLRenderer(BaseRenderer):
    media_type = "application/xml"

    def render(self, request, data, *, response_status):
        stream = StringIO()
        xml = SimplerXMLGenerator(stream, "utf-8")
        xml.startDocument()
        xml.startElement("data", {})

        def _to_xml(parent_xml, value):
            if isinstance(value, dict):
                for key, val in value.items():
                    parent_xml.startElement(key, {})
                    _to_xml(parent_xml, val)
                    parent_xml.endElement(key)
            elif isinstance(value, list):
                for item in value:
                    _to_xml(parent_xml, item)
            else:
                parent_xml.characters(str(value))

        _to_xml(xml, data)
        xml.endElement("data")
        xml.endDocument()
        return stream.getvalue()
