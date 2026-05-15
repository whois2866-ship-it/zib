# TikTok Account Creator

Automated TikTok account creation using Playwright, CapSolver (CAPTCHA solving), Postal (self-hosted email), and proxy rotation.

## Features

- **Playwright browser automation** — navigates TikTok signup flow
- **CapSolver CAPTCHA solving** — handles FunCaptcha and slider puzzles
- **Postal email integration** — receives verification codes via self-hosted mail server (`mail.botwave.online`)
- **Webshare proxy rotation** — rotates through proxy list to avoid IP bans
- **Advanced stealth mode** — spoofs WebGL, plugins, navigator properties, randomizes fingerprints
- **User-agent rotation** — realistic UA strings via `fake-useragent`
- **Automatic retries** — configurable retry count with increasing delays
- **Concurrent creation** — create multiple accounts simultaneously
- **Headless mode** — run without visible browser window
- **Account warming** — post-signup activity (scrolling, liking, watching) to build account legitimacy
- **Structured logging** — console + rotating log files in `logs/`
- **CSV output** — saves created accounts to `accounts.csv`
- **CLI interface** — full-featured command-line usage
- **Mass unfollow tool** — bonus script to bulk unfollow accounts

## Prerequisites

- Python 3.10+
- [CapSolver API key](https://www.capsolver.com/) for CAPTCHA solving
- Postal mail server (already configured at `postal.botwave.online`)
- Proxies (Webshare format in `proxies.txt`)

## Setup

```bash
# Clone the repo
git clone https://github.com/YOUR_USERNAME/zib.git
cd zib

# Install dependencies
pip install -r requirements.txt
playwright install chromium

# Configure
cp .env.example .env
# Edit .env with your API keys
```

## Configuration

Edit `.env` with your credentials:

```env
CAPSOLVER_API_KEY=your_key_here
POSTAL_URL=https://postal.botwave.online
POSTAL_API_KEY=your_postal_server_api_key

# Retry settings
MAX_RETRIES=3
RETRY_DELAY=10

# Concurrency
MAX_CONCURRENT=1
```

### Proxies

Add proxies to `proxies.txt` in Webshare format:
```
host:port:username:password
```

Or standard URL format:
```
http://user:pass@host:port
```

## Usage

```bash
# Create 1 account
python create_accounts.py --count 1

# Create 5 accounts
python create_accounts.py --count 5

# Create 10 accounts, 3 at a time, headless
python create_accounts.py --count 10 --concurrent 3 --headless

# Use specific email list
python create_accounts.py --count 3 --emails emails.txt

# Use a single specific email
python create_accounts.py --count 1 --email myemail@mail.botwave.online

# Mass unfollow (reduce following count)
python tiktok_unfollow.py
```

## Project Structure

```
config.py            — Settings loaded from .env
captcha_solver.py    — CapSolver API + slider CAPTCHA fallback
email_handler.py     — Postal API + IMAP + email list handling
proxy_manager.py     — Proxy rotation (Webshare + URL formats)
signup_flow.py       — Main Playwright signup automation
create_accounts.py   — CLI entry point
stealth.py           — Browser fingerprint spoofing & anti-detection
account_warmer.py    — Post-signup account warming actions
logger.py            — Centralized logging (console + file)
tiktok_unfollow.py   — Mass unfollow automation tool
proxies.txt          — Your proxy list (not committed)
accounts.csv         — Created accounts output (not committed)
```

## How It Works

1. Launches Chromium with a random proxy, fingerprint, and user-agent
2. Navigates to TikTok email signup page
3. Fills in birthday (from config)
4. Enters a random `@mail.botwave.online` email and password
5. Detects and solves CAPTCHA via CapSolver API
6. Submits signup form
7. Polls Postal API for incoming TikTok verification code
8. Enters verification code to complete signup
9. Sets username and saves account details to CSV
10. Optionally warms the account (scrolling, liking, watching)
11. Retries on failure (up to `MAX_RETRIES` times)
12. Waits increasing delays between accounts to avoid detection

## Output

Created accounts are saved to `accounts.csv`:
```csv
email,password,username,status
abc123@mail.botwave.online,YourPass123,user_abc123,success
```

Logs are saved to `logs/tiktok_creator.log` (rotating, 5 MB max).

## Notes

- TikTok has aggressive anti-bot detection — success rate varies
- Use quality residential proxies for best results
- Increasing delays between accounts reduces ban risk
- The CAPTCHA solving adds ~$0.002-0.005 per solve via CapSolver
- Some signups may fail due to TikTok's detection — the tool logs failures and continues
- Concurrent mode (`--concurrent N`) is experimental — lower concurrency is safer
