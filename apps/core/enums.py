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