from enum import IntEnum

class QuestionType(IntEnum):
    MCQ = 0
    EITHER_OR = 1
    SHORT_ANSWER = 2
    ESSAY_QUESTION = 3
    TEXT_FILLER = 4

    @classmethod
    def choices(cls):
        return [(cls.value,cls.name) for cls in QuestionType]
