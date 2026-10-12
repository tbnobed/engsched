"""Plain, professional presentation for AI-generated text."""
import re
from html import escape

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


def format_ai_response(content):
    """Render the assistant's plain text / basic Markdown without trusting HTML."""
    def inline(text):
        text = escape(text)
        text = re.sub(r"`([^`\n]+)`", r"<code>\1</code>", text)
        return re.sub(r"\*\*([^*\n]+)\*\*", r"<strong>\1</strong>", text)

    sections = r"(?:summary|possible causes(?:\s*\(ranked\))?|likely causes|safe diagnostic steps|diagnostic steps|suggested solutions|next steps|questions(?: for missing facts)?|clarifying questions|confidence level|analysis)"
    output, paragraph, list_kind = [], [], None

    def flush():
        if paragraph:
            output.append("<p>" + "<br>".join(paragraph) + "</p>")
            paragraph.clear()

    def close_list():
        nonlocal list_kind
        if list_kind:
            output.append("</" + list_kind + ">")
            list_kind = None

    for raw in without_emojis(content).splitlines():
        line = raw.strip()
        if not line:
            flush()
            close_list()
            continue
        heading = re.match(r"^#{1,6}\s+(.+)$", line)
        plain_heading = line.strip("*").strip().rstrip(":").strip()
        if heading or re.fullmatch(sections, plain_heading, flags=re.I):
            flush()
            close_list()
            output.append("<h5>" + inline(heading.group(1) if heading else plain_heading) + "</h5>")
            continue
        item = re.match(r"^(?:(\d+)[.)]|([-*•]))\s+(.+)$", line)
        if item:
            flush()
            kind = "ol" if item.group(1) else "ul"
            if list_kind != kind:
                close_list()
                output.append(f'<ol start="{int(item.group(1))}">' if kind == "ol" else "<ul>")
                list_kind = kind
            output.append("<li>" + inline(item.group(3)) + "</li>")
        else:
            close_list()
            paragraph.append(inline(line))
    flush()
    close_list()
    return "".join(output)
