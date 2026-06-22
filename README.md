# 🦊 GoMine Bot

GoMine Telegram Mini App automation — multi-account login, daily checkin, ads claiming.

## ⚡ Key Insight

Monetag (ads SDK) blocks Chromium headless (204 response). **Firefox headless passes** (200). This is the only working method.

## 📦 Setup

```bash
# Install dependencies
pip install playwright
playwright install firefox

# Setup SOCKS5 proxy (Indonesian IP required for Monetag)
# Option 1: SSH tunnel
ssh -D 1080 -N user@your-server

# Option 2: sshuttle
sshuttle -r user@your-server 0/0

# Copy example auth file
cp auth.txt.example auth.txt
# Edit auth.txt — add your initData (1 per line)
```

## 🚀 Usage

```bash
# Full flow: login → profile → checkin → ads
python3 gomine_bot.py

# Skip ads
python3 gomine_bot.py --no-ads

# Max 5 ads
python3 gomine_bot.py --max-ads 5

# HTTP-only (no ads, no browser)
python3 gomine_auto.py --checkin --tasks
```

## 📋 Flow

1. **Login** — POST `/api/users/init` with `X-Init-Data` header
2. **Profile** — Display username, points, sparks, streak, tier, balance
3. **Daily Checkin** — POST `/api/checkin`
4. **Ads Loop** (Firefox):
   - Click "▶ Watch" button on Earn tab
   - Wait for Monetag SDK to load ad (8s)
   - Interact with ad (click buttons, 35s)
   - Claim reward via POST `/api/ads/claim`
   - Wait cooldown (155s) + refresh page
   - Repeat for remaining ads
5. **Summary** — Display total earned

## 🔑 API Reference

| Endpoint | Method | Description |
|---|---|---|
| `/api/users/init` | POST | Login, get profile |
| `/api/checkin` | POST | Daily checkin |
| `/api/ads/status` | GET | Ads remaining, cooldown |
| `/api/ads/start` | POST | Get ad token |
| `/api/ads/claim` | POST | Claim reward |
| `/api/users/burns` | GET | Balance |

Auth: `X-Init-Data` header (Telegram initData)

## 📁 Files

| File | Description |
|---|---|
| `gomine_bot.py` | Main bot — full flow with Firefox ads |
| `gomine_auto.py` | HTTP-only — checkin, tasks, ads status |
| `auth.txt.example` | Example auth file format |
| `auth.txt` | Your initData (git-ignored) |

## 🛡️ Anti-Fingerprint

| Browser | Monetag Response | Status |
|---|---|---|
| Chromium headless | 204 | ❌ Blocked |
| Chromium + Stealth | 200 | ✅ Works |
| Firefox headless | 200 | ✅ Works + Claimed |

## ⚠️ Requirements

- Python 3.12+
- Playwright with Firefox
- SOCKS5 proxy with Indonesian IP
- Telegram initData (via Telethon or manual)

## 📝 Notes

- Daily ads quota: 10/day
- Cooldown between ads: ~155 seconds
- Reward range: 0-5000 milliGOMINE per ad
- Reset: midnight UTC
