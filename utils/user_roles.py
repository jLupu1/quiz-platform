from enum import IntEnum

class UserRole(IntEnum):
    STUDENT = 0
    TEACHER = 1
    ADMIN = 2

    @classmethod
    def choices(cls):
        return [(cls.value,cls.name) for cls in UserRole]

