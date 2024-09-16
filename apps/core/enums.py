from enum import Enum


class BaseEnum(Enum):
    @classmethod
    def choices(cls):
        return [(item.name, item.value) for item in cls]
    @classmethod
    def values(cls):
        return [item.value for item in cls]
