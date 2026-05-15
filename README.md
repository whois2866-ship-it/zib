# TikTok Account Creator
 
Automated TikTok account creation using Playwright, CapSolver (CAPTCHA solving), Postal (self-hosted email), and proxy rotation.
 
## Features
 
- **Playwright browser automation** — navigates TikTok signup flow
- **CapSolver CAPTCHA solving** — handles FunCaptcha and slider puzzles
- **Postal email integration** — receives verification codes via self-hosted mail server (`mail.botwave.online`)
- **Webshare proxy rotation** — rotates through proxy list to avoid IP bans
- **Stealth mode** — removes webdriver flags, randomizes delays, mimics human typing
- **CSV output** — saves created accounts to `accounts.csv`
- **CLI interface** — simple command-line usage
 
## Prerequisites
 
- Python 3.10+
- [CapSolver API key](https://www.capsolver.com/) for CAPTCHA solving
- Postal mail server (already configured at `postal.botwave.online`)
- Proxies (Webshare format in `proxies.txt`)
 
## Setup
 
```bash
# Clone the repo
git clone https://github.com/YOUR_USERNAME/tiktok-account-creator.git
cd tiktok-account-creator
 
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
 
# Use specific email list
python create_accounts.py --count 3 --emails emails.txt
 
# Use a single specific email
python create_accounts.py --count 1 --email myemail@mail.botwave.online
```
 
## Project Structure
 
```
config.py            — Settings loaded from .env
captcha_solver.py    — CapSolver API + slider CAPTCHA fallback
email_handler.py     — Postal API + IMAP + email list handling
proxy_manager.py     — Proxy rotation (Webshare + URL formats)
signup_flow.py       — Main Playwright signup automation
create_accounts.py   — CLI entry point
proxies.txt          — Your proxy list (not committed)
accounts.csv         — Created accounts output (not committed)
```
 
## How It Works
 
1. Launches Chromium with a proxy and stealth settings
2. Navigates to TikTok email signup page
3. Fills in birthday (from config)
4. Enters a random `@mail.botwave.online` email and password
5. Detects and solves CAPTCHA via CapSolver API
6. Submits signup form
7. Polls Postal API for incoming TikTok verification code
8. Enters verification code to complete signup
9. Sets username and saves account details to CSV
10. Waits increasing delays between accounts to avoid detection
 
## Output
 
Created accounts are saved to `accounts.csv`:
```csv
email,password,username,status
abc123@mail.botwave.online,YourPass123,user_abc123,success
```
 
## Notes
 
- TikTok has aggressive anti-bot detection — success rate varies
- Use quality residential proxies for best results
- Increasing delays between accounts reduces ban risk
- The CAPTCHA solving adds ~$0.002-0.005 per solve via CapSolver
- Some signups may fail due to TikTok's detection — the tool logs failures and continues
