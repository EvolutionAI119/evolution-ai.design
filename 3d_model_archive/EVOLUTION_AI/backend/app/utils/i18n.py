from fastapi import Header

from app.locale import Translator
from app.config.settings import settings


def get_translator(accept_language: str = Header(None)) -> Translator:
    lang = _resolve_language(accept_language)
    return Translator(lang)


def get_t(accept_language: str = Header(None)):
    translator = get_translator(accept_language)
    return translator.t


def _resolve_language(accept_language: str) -> str:
    if accept_language:
        resolved = Translator.get_lang_from_header(accept_language)
        if resolved in settings.supported_languages_list:
            return resolved
    return settings.DEFAULT_LANGUAGE
