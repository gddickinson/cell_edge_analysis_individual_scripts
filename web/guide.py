"""The desktop GUI's Help -> Analysis Guide text (gui_help_content.HELP_SECTIONS) for the web Guide page."""
import re

import gui_help_content


def _slug(title):
    return re.sub(r"[^a-z0-9]+", "-", title.lower()).strip("-")


def sections():
    """[{id, title, body}] in the GUI's order; body is the GUI's plain text, unchanged."""
    return {"sections": [{"id": _slug(t), "title": t, "body": b} for t, b in gui_help_content.HELP_SECTIONS],
            "about": gui_help_content.ABOUT_TEXT}
