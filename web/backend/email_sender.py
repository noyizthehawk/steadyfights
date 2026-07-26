import os
import resend

from .config import EMAIL_FROM, FRONTEND_URL, RESEND_API_KEY

# Initialize API Key (Will automatically check RESEND_API_KEY env if not set here)
resend.api_key = RESEND_API_KEY


async def send_email(to: str, subject: str, html: str) -> dict:
    """Low-level send. Every caller supplies its own subject + body."""
    return await resend.Emails.send_async({
        "from": EMAIL_FROM,
        "to": to,
        "subject": subject,
        "html": html,
    })

async def send_friend_request_email(to: str, from_email: str) -> dict:
    subject = f"{from_email} sent you a friend request on SteadyFights"
    html = (
        f"<p><strong>{from_email}</strong> wants to be your friend on SteadyFights.</p>"
        f'<p><a href="{FRONTEND_URL}/friends">View your invites</a></p>'
    )
    return await send_email(to, subject, html)
   
   