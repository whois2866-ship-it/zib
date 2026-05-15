"""
Email handling module for receiving TikTok verification codes.
Supports:
- Postal API (self-hosted mail server)
- IMAP (Gmail, Outlook, custom)
- Pre-generated email list
"""
 
import asyncio
import email
import imaplib
import re
import time
 
import httpx
from config import Config
 
 
class PostalEmailHandler:
    """
    Use Postal (self-hosted mail server) API to create addresses
    and fetch incoming verification emails.
    Postal docs: https://docs.postalserver.io/developer/api
    """
 
    def __init__(self):
        self.base_url = Config.POSTAL_URL.rstrip("/")
        self.api_key = Config.POSTAL_API_KEY
 
    @property
    def headers(self):
        return {
            "X-Server-API-Key": self.api_key,
            "Content-Type": "application/json",
        }
 
    async def get_messages(self, email_address: str, timeout: int = 120, poll_interval: int = 5) -> str | None:
        """
        Poll Postal API for incoming TikTok verification email.
        Returns the 6-digit code or None.
        """
        async with httpx.AsyncClient(timeout=15) as client:
            start = time.time()
            while time.time() - start < timeout:
                try:
                    resp = await client.post(
                        f"{self.base_url}/api/v1/messages",
                        headers=self.headers,
                        json={"to": email_address, "limit": 5},
                    )
                    data = resp.json()
                    messages = data.get("data", [])
 
                    for msg in messages:
                        msg_id = msg.get("id")
                        if not msg_id:
                            continue
 
                        # Fetch full message
                        detail_resp = await client.post(
                            f"{self.base_url}/api/v1/messages/message",
                            headers=self.headers,
                            json={"id": msg_id, "expansions": ["plain_body", "html_body"]},
                        )
                        detail = detail_resp.json().get("data", {})
                        subject = detail.get("subject", "").lower()
                        from_addr = detail.get("from", "").lower()
                        body = detail.get("plain_body", "") or detail.get("html_body", "")
 
                        if "tiktok" in subject or "tiktok" in from_addr or "verification" in subject:
                            match = re.search(r"\b(\d{6})\b", body)
                            if match:
                                code = match.group(1)
                                print(f"  Verification code found: {code}")
                                return code
 
                except Exception as e:
                    print(f"  Postal API error: {e}")
 
                await asyncio.sleep(poll_interval)
 
        print("  Verification code timeout")
        return None
 
 
class IMAPEmailHandler:
    """Fetch verification codes from a real email inbox via IMAP."""
 
    def __init__(self, address: str = "", password: str = ""):
        self.server = Config.EMAIL_IMAP_SERVER
        self.port = Config.EMAIL_IMAP_PORT
        self.address = address or Config.EMAIL_ADDRESS
        self.password = password or Config.EMAIL_PASSWORD
 
    def get_verification_code(self, timeout: int = 120, poll_interval: int = 5) -> str | None:
        """
        Poll IMAP inbox for a TikTok verification email.
        Returns the 6-digit code or None.
        """
        start = time.time()
        while time.time() - start < timeout:
            try:
                mail = imaplib.IMAP4_SSL(self.server, self.port)
                mail.login(self.address, self.password)
                mail.select("inbox")
 
                _, data = mail.search(None, '(FROM "tiktok" UNSEEN)')
                email_ids = data[0].split()
 
                if email_ids:
                    _, msg_data = mail.fetch(email_ids[-1], "(RFC822)")
                    msg = email.message_from_bytes(msg_data[0][1])
 
                    body = ""
                    if msg.is_multipart():
                        for part in msg.walk():
                            if part.get_content_type() == "text/plain":
                                body = part.get_payload(decode=True).decode()
                                break
                            elif part.get_content_type() == "text/html":
                                body = part.get_payload(decode=True).decode()
                    else:
                        body = msg.get_payload(decode=True).decode()
 
                    match = re.search(r"\b(\d{6})\b", body)
                    if match:
                        code = match.group(1)
                        print(f"  Verification code found: {code}")
                        mail.logout()
                        return code
 
                mail.logout()
            except Exception as e:
                print(f"  IMAP error: {e}")
 
            time.sleep(poll_interval)
 
        print("  Verification code timeout")
        return None
 
 
class EmailListHandler:
    """Handle a list of pre-generated email addresses from a file."""
 
    def __init__(self, filepath: str = "emails.txt"):
        self.filepath = filepath
        self.emails: list[str] = []
        self._load()
 
    def _load(self):
        try:
            with open(self.filepath) as f:
                self.emails = [
                    line.strip() for line in f if line.strip() and "@" in line
                ]
            print(f"Loaded {len(self.emails)} emails from {self.filepath}")
        except FileNotFoundError:
            print(f"No {self.filepath} found. Create one with emails (one per line).")
 
    def next_email(self) -> str | None:
        if not self.emails:
            return None
        return self.emails.pop(0)
 
    def remaining(self) -> int:
        return len(self.emails)
