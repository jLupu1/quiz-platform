from enum import IntEnum

class QuestionStatus(IntEnum):
    PENDING = 0
    IN_MARKING = 1
    MARKED = 2

    @classmethod
    def choices(cls):
        return [(cls.value,cls.name) for cls in QuestionStatus]