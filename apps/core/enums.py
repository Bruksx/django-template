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
    def get_index(cls, item:str):
        if hasattr(item, 'value'):
            item = item.value
        elif str(item).startswith("PhaseType"):
            item = str(item).split(".")[-1]
        for i,val in enumerate(cls):
            if str(val.value).lower() == str(item).lower():
                return i
        return

    @classmethod
    def from_index(cls, index):
        for i, x in enumerate(cls):
            if i == index:
                return x
        return


    @classmethod
    def get(cls, value):
        for item in cls.values():
            if str(item).lower() == str(value).lower():
                return item
        return None





class SalaryType(BaseEnum):
    HOURLY = "Hourly"
    DAILY = "Daily"
    WEEKLY = "Weekly"
    BI_WEEKLY = "Bi-Weekly"
    MONTHLY = "Monthly"
    BI_MONTHLY = "Bi-Monthly"
    ANNUALLY = "Annually"
