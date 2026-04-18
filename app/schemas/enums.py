from enum import Enum

class JobSource(str, Enum):
    DJINNI = "djinni"
    DOU = "dou"
    LINKEDIN = "linkedin"