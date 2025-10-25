import xml.etree.ElementTree as ET
from dataclasses import is_dataclass, asdict


def dict_to_xml(parent, data):
    """Recursively add dataclass or dict to XML."""
    if is_dataclass(data):
        data = asdict(data)

    for key, value in data.items():
        if isinstance(value, list):
            container = ET.SubElement(parent, key)
            for item in value:
                item_elem = ET.SubElement(container, key[:-1])
                dict_to_xml(item_elem, item)
        elif isinstance(value, dict):
            child = ET.SubElement(parent, key)
            dict_to_xml(child, value)
        else:
            ET.SubElement(parent, key).text = str(value)
