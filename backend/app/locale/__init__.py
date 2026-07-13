from .zh import messages as zh_messages
from .en import messages as en_messages

_locales = {
    "zh": zh_messages,
    "en": en_messages
}


def get_message(key: str, lang: str = "zh") -> str:
    messages = _locales.get(lang, zh_messages)
    return messages.get(key, key)


class Translator:
    def __init__(self, lang: str = "zh"):
        self.lang = lang

    def t(self, key: str) -> str:
        return get_message(key, self.lang)

    @staticmethod
    def get_lang_from_header(accept_language: str) -> str:
        if not accept_language:
            return "zh"
        languages = accept_language.split(",")
        for lang in languages:
            parts = lang.strip().split(";")
            locale = parts[0].lower()
            if locale.startswith("zh"):
                return "zh"
            elif locale.startswith("en"):
                return "en"
        return "zh"

    @classmethod
    def from_header(cls, accept_language: str):
        lang = cls.get_lang_from_header(accept_language)
        return cls(lang)
