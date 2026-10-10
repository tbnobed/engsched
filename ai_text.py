"""Plain, professional presentation for AI-generated text."""
import re

_EMOJI = re.compile(
    "[\U0001F000-\U0001FAFF\u2600-\u27BF\u200D\uFE0F\u20E3]"
)


def without_emojis(text):
    return _EMOJI.sub("", text or "")


def clean_legacy_analysis(content):
    # Preserve ordinary user comments, including any emojis they chose.
    if (content or "").startswith(("<p><strong>🤖 AI Analysis", "<p><strong>AI Analysis")):
        return without_emojis(content)
    return content
