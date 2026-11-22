"""Render every email to HTML files and open them in the browser — no sending.

    python -m web.backend.email_preview            # writes + opens
    python -m web.backend.email_preview --no-open

The header image loads from FRONTEND_URL, so run the frontend (npm run dev)
to see the logo locally.
"""
import sys
import tempfile
import webbrowser
from pathlib import Path

from .email_sender import friend_request_email, welcome_email

SAMPLES = {
    "welcome": welcome_email("noya"),
    "friend_request": friend_request_email("steadyfan99"),
}


def main() -> None:
    out = Path(tempfile.gettempdir()) / "steadyfights-email-preview"
    out.mkdir(exist_ok=True)
    for name, (subject, html) in SAMPLES.items():
        path = out / f"{name}.html"
        path.write_text(html)
        print(f"{name:16} {subject!r}\n{'':16} {path}")
        if "--no-open" not in sys.argv:
            webbrowser.open(path.as_uri())


if __name__ == "__main__":
    main()
