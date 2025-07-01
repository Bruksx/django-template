from enum import Enum


class BaseEnum(Enum):
    @classmethod
    def choices(cls):
        return [(item.value, item.value) for item in cls]

    @classmethod
    def values(cls):
        return [item.value for item in cls]

    @classmethod
    def indices(cls):
        return [i for i, x in enumerate(cls)]

    @classmethod
    def get(cls, value):
        for item in cls.values():
            if str(item).lower() == str(value).lower():
                return item
        return None