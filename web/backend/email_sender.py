"""Transactional email via Resend.

Every email goes through `render()`: one shared, on-brand layout (black card,
red rule, logo header as an image so it looks the same in every mail app).
Email HTML is old-school on purpose — tables and inline styles only, because
Gmail/Outlook strip <style> blocks, flexbox and web fonts.

Preview without sending:  python -m web.backend.email_preview
"""
from html import escape

import resend

from .config import EMAIL_FROM, FRONTEND_URL, RESEND_API_KEY

resend.api_key = RESEND_API_KEY

RED = "#d33a2c"
BG = "#000000"
CARD = "#0a0a0a"
LINE = "#262626"
TEXT = "#e4e4e7"
MUTED = "#a1a1aa"
FAINT = "#71717a"
SANS = "'Helvetica Neue', Helvetica, Arial, sans-serif"
MONO = "'SF Mono', Menlo, Consolas, 'Courier New', monospace"


def render(*, preheader: str, eyebrow: str, heading: str, body: str,
           cta_label: str, cta_url: str) -> str:
    """The shared layout. `body` is trusted HTML built by the caller; escape any
    user-supplied value (usernames!) before putting it in."""
    base = FRONTEND_URL.rstrip("/")
    return f"""<!doctype html>
<html lang="en">
<head>
<meta charset="utf-8">
<meta name="viewport" content="width=device-width, initial-scale=1">
<meta name="color-scheme" content="dark">
<meta name="supported-color-schemes" content="dark">
<title>{escape(heading)}</title>
</head>
<body style="margin:0;padding:0;background:{BG};">
<div style="display:none;max-height:0;overflow:hidden;opacity:0;color:{BG};">{escape(preheader)}&#8199;&#847;&#8199;&#847;&#8199;&#847;&#8199;&#847;</div>
<table role="presentation" width="100%" cellpadding="0" cellspacing="0" border="0" style="background:{BG};">
<tr><td align="center" style="padding:32px 16px;">
  <table role="presentation" width="100%" cellpadding="0" cellspacing="0" border="0" style="max-width:520px;background:{CARD};border:1px solid {LINE};border-radius:12px;">
    <tr><td style="padding:28px 32px 0;">
      <a href="{base}" style="text-decoration:none;"><img src="{base}/email/header.png" width="250" height="44" alt="STEADYFIGHTS" style="display:block;border:0;width:250px;height:44px;color:#ffffff;font:bold 16px {MONO};"></a>
    </td></tr>
    <tr><td style="padding:24px 32px 0;">
      <div style="height:2px;line-height:2px;font-size:0;background:{RED};">&nbsp;</div>
    </td></tr>
    <tr><td style="padding:24px 32px 0;font:600 11px/1 {MONO};letter-spacing:2px;text-transform:uppercase;color:{RED};">
      {escape(eyebrow)}
    </td></tr>
    <tr><td style="padding:12px 32px 0;font:800 28px/1.15 {SANS};color:#ffffff;letter-spacing:-0.5px;">
      {heading}
    </td></tr>
    <tr><td style="padding:16px 32px 0;font:400 15px/1.6 {SANS};color:{TEXT};">
      {body}
    </td></tr>
    <tr><td style="padding:28px 32px 32px;">
      <table role="presentation" cellpadding="0" cellspacing="0" border="0"><tr>
        <td style="background:{RED};border-radius:6px;">
          <a href="{cta_url}" style="display:inline-block;padding:13px 22px;font:700 12px/1 {MONO};letter-spacing:1.5px;text-transform:uppercase;color:#000000;text-decoration:none;">{escape(cta_label)} &rarr;</a>
        </td>
      </tr></table>
    </td></tr>
  </table>
  <table role="presentation" width="100%" cellpadding="0" cellspacing="0" border="0" style="max-width:520px;">
    <tr><td style="padding:18px 32px 0;font:400 11px/1.7 {MONO};color:{FAINT};">
      <a href="{base}" style="color:{MUTED};text-decoration:none;">steadyfights.com</a>
      &nbsp;&middot;&nbsp;
      <a href="{base}/privacy" style="color:{FAINT};text-decoration:underline;">Privacy</a><br>
      You're getting this because you have a SteadyFights account.
    </td></tr>
  </table>
</td></tr>
</table>
</body>
</html>"""


# ---- the emails ------------------------------------------------------------

def welcome_email(username: str) -> tuple[str, str]:
    name = escape(username)
    base = FRONTEND_URL.rstrip("/")
    html = render(
        preheader="Make your picks, climb the board, call the upsets.",
        eyebrow="You're on the card",
        heading=f"Welcome in, {name}.",
        body=(
            "Pick every fight on the next UFC card, earn points when you're right, "
            "and climb the leaderboard against everyone else, your friends included."
            f'<br><br><span style="color:{MUTED};">Want a second opinion? Bout Brain is the '
            "most honest prediction model in the game. It's graded only on fights it "
            "never saw, misses included. No cherry picking, ever.</span>"
        ),
        cta_label="Make your picks",
        cta_url=f"{base}/prediction-game",
    )
    return "Welcome to SteadyFights", html


def friend_request_email(from_username: str) -> tuple[str, str]:
    name = escape(from_username)
    base = FRONTEND_URL.rstrip("/")
    html = render(
        preheader=f"{from_username} wants to go head to head on picks.",
        eyebrow="Friend request",
        heading=f"{name} wants to square up.",
        body=(
            f"<strong style=\"color:#ffffff;\">{name}</strong> sent you a friend request. "
            "Accept it to see each other's picks and go head to head on the leaderboard."
        ),
        cta_label="View invite",
        cta_url=f"{base}/friends",
    )
    return f"{from_username} sent you a friend request", html


# ---- sending ---------------------------------------------------------------

async def send_email(to: str, subject: str, html: str) -> dict:
    """Low-level send. Every caller supplies its own subject + body."""
    return await resend.Emails.send_async({
        "from": EMAIL_FROM,
        "to": to,
        "subject": subject,
        "html": html,
    })


async def send_welcome_email(to: str, username: str) -> dict:
    subject, html = welcome_email(username)
    return await send_email(to, subject, html)


async def send_friend_request_email(to: str, from_username: str) -> dict:
    subject, html = friend_request_email(from_username)
    return await send_email(to, subject, html)
