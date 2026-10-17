"""The languages a paper can be read in: English and Simplified Chinese. English is the base every translation is
built from. A translation of any other language, stored before the reader offered only these two, stays on disk but is
neither offered nor read (store.languages).

Budgets are per script: a language written without spaces counts characters, the other counts words.
"""

# code: (name used in prompts, native name, script)
LANGS = {
    "en": ("English", "English", "latin"),
    "zh": ("Simplified Chinese", "简体中文", "cjk"),
}

_CHARS = {"takeaway": 28, "reason": 50, "topic": 6, "section": 32, "unit": "characters"}
_WORDS = {"takeaway": 16, "reason": 26, "topic": 4, "section": 18, "unit": "words"}


def name(code):
    return LANGS[code][0]


def budget(code):
    return _CHARS if cjk(code) else _WORDS


def cjk(code):
    return LANGS[code][2] == "cjk"


def stop(code):
    """The full stop that joins the takeaway and the reason in Brief."""
    return "。" if cjk(code) else "."


def punctuation_rule(code):
    n = name(code)
    if code == "zh":
        return f"{n} full-width punctuation; no dashes (——)."
    return f"Standard {n} punctuation; no em or en dashes as punctuation, use commas or colons."
