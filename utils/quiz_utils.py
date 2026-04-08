from enum import IntEnum

class QuizOpenStatus(IntEnum):
    CLOSED = 0
    OPEN = 1

    @classmethod
    def choices(cls):
        return [(cls.value,cls.name) for cls in QuizOpenStatus]

class QuizMarkingStatus(IntEnum):
    PENDING = 0
    MARKED = 1

    @classmethod
    def choices(cls):
        return [(cls.value, cls.name) for cls in QuizMarkingStatus]