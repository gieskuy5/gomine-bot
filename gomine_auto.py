#!/usr/bin/env python3
"""
GoMine Auto Bot — login via Telegram initData from Telethon session
Usage:
    python3 gomine_auto.py                # Run once (checkin + ads)
    python3 gomine_auto.py --loop         # Loop forever (6h interval)
    python3 gomine_auto.py --tasks        # List available tasks
    python3 gomine_auto.py --claim-ads    # Watch & claim all available ads
"""

import sys, json, time, argparse, urllib.parse
sys.path.insert(0, '/home/ubuntu/BOT/telegram-client')

import requests
from telethon import TelegramClient
from telethon.tl.functions.messages import RequestWebViewRequest

# --- Config ---
CONFIG_PATH = '/home/ubuntu/BOT/telegram-client/config/telethon.json'
API_BASE = 'https://app.gomine.social/api'
BOT_USERNAME = 'GoMineAppBot'
WEBAPP_URL = 'https://app.gomine.social/'


def load_telethon_config():
    with open(CONFIG_PATH) as f:
        return json.load(f)


def get_init_data(cfg):
    """Get fresh initData via Telethon RequestWebView"""
    import asyncio

    async def _get():
        client = TelegramClient(cfg['session_path'], cfg['api_id'], cfg['api_hash'])
        await client.start()
        bot = await client.get_entity(BOT_USERNAME)
        result = await client(RequestWebViewRequest(
            peer=bot,
            bot=bot,
            url=WEBAPP_URL,
            platform='android',
            theme_params=None
        ))
        await client.disconnect()
        # Extract tgWebAppData from URL fragment
        url = result.url
        fragment = url.split('#')[1]
        params = urllib.parse.parse_qs(fragment)
        init_data = urllib.parse.unquote(params['tgWebAppData'][0])
        return init_data

    return asyncio.get_event_loop().run_until_complete(_get())


class GoMineAPI:
    def __init__(self, init_data):
        self.init_data = init_data
        self.session = requests.Session()
        self.session.headers.update({
            'X-Init-Data': init_data,
            'Content-Type': 'application/json',
            'User-Agent': 'Mozilla/5.0 (Linux; Android 14) AppleWebKit/537.36'
        })

    def _get(self, path):
        r = self.session.get(f'{API_BASE}{path}')
        r.raise_for_status()
        return r.json()

    def _post(self, path, data=None):
        r = self.session.post(f'{API_BASE}{path}', json=data or {})
        r.raise_for_status()
        return r.json()

    # --- User ---
    def init(self):
        return self._post('/users/init')

    def me(self):
        return self._get('/users/me')

    def checkin(self):
        return self._post('/users/checkin')

    # --- Ads ---
    def ads_status(self):
        return self._get('/ads/status')

    def ads_start(self):
        return self._post('/ads/start')

    def ads_claim(self, token=''):
        return self._post('/ads/claim', {'token': token} if token else {})

    # --- Campaigns / Tasks ---
    def campaigns(self):
        return self._get('/campaigns')

    def campaigns_browse(self):
        return self._get('/campaigns/browse')

    # --- Referral ---
    def referral_link(self):
        return self._get('/referral/link')

    def referral_stats(self):
        return self._get('/referral/stats')

    # --- Holder Boost ---
    def holder_boost_state(self):
        return self._get('/users/holder-boost/state')


def print_user(user):
    print(f"\n👤 {user['first_name']} (@{user['username']})")
    print(f"   ⚡ Sparks: {user['sparks']} | 🔥 Streak: {user['streak_days']}d")
    print(f"   🏷️ Tier: {user['access_tier_name']} | 💰 Points: {user['points']}")
    print(f"   💎 Wallet: {user['wallet_address'][:20]}...")
    if user.get('twitter_username'):
        print(f"   🐦 X: @{user['twitter_username']}")
    else:
        print(f"   🐦 X: ❌ Not connected")


def do_checkin(api):
    """Daily checkin"""
    try:
        result = api.checkin()
        if result.get('success'):
            print(f"   ✅ Checkin: +{result['sparks_awarded']} sparks | Streak: {result['streak_days']}d")
        else:
            print(f"   ℹ️ Checkin: {result}")
    except requests.HTTPError as e:
        if e.response.status_code == 400:
            print("   ℹ️ Checkin: Sudah hari ini")
        else:
            print(f"   ❌ Checkin error: {e}")


def do_ads(api, max_ads=10):
    """Check ads status only — actual claiming requires browser Monetag SDK"""
    status = api.ads_status()
    remaining = status.get('remaining_today', 0)
    enabled = status.get('enabled', False)
    print(f"\n📺 Ads Status: {'✅ Enabled' if enabled else '❌ Disabled'}")
    print(f"   Remaining: {remaining}/{status.get('daily_cap', '?')} today")
    print(f"   ⚠️ Ads claim requires browser (Monetag SDK) — HTTP claim stays 'pending'")
    return 0


def list_tasks(api):
    """List available campaigns and tasks"""
    campaigns = api.campaigns()
    browse = api.campaigns_browse()

    print("\n📋 Campaigns:")
    for c in campaigns:
        print(f"   {'⭐' if c.get('featured') else '📌'} [{c['id']}] {c['name']} — {c['participants']} participants, {c['available_points']} pts available")

    print("\n📊 Tasks by Platform:")
    for cat in browse:
        platform = cat['platform']
        count = cat['count']
        remaining = cat['sum_remaining']
        print(f"\n   🔹 {platform} ({count} tasks, {remaining} pts remaining)")
        for action in cat.get('actions', []):
            print(f"      - {action['action']}: {action['count']} tasks ({action['sum_remaining']} pts)")


def main():
    parser = argparse.ArgumentParser(description='GoMine Auto Bot')
    parser.add_argument('--loop', action='store_true', help='Loop forever')
    parser.add_argument('--interval', type=int, default=21600, help='Loop interval (seconds, default 6h)')
    parser.add_argument('--tasks', action='store_true', help='List tasks only')
    parser.add_argument('--claim-ads', action='store_true', help='Claim ads')
    parser.add_argument('--max-ads', type=int, default=10, help='Max ads to claim')
    parser.add_argument('--status', action='store_true', help='Show user status')
    args = parser.parse_args()

    cfg = load_telethon_config()

    def run_once():
        print(f"\n{'='*50}")
        print(f"⏰ {time.strftime('%Y-%m-%d %H:%M:%S')}")
        print(f"{'='*50}")

        # Get fresh initData
        print("🔑 Getting initData from Telethon...")
        init_data = get_init_data(cfg)
        api = GoMineAPI(init_data)

        # Init user
        user = api.init()
        print_user(user)

        if args.status:
            return

        if args.tasks:
            list_tasks(api)
            return

        # Daily checkin
        print("\n📅 Daily Checkin:")
        do_checkin(api)

        # Ads
        if args.claim_ads:
            do_ads(api, args.max_ads)
        else:
            # Auto claim ads by default
            status = api.ads_status()
            if status.get('remaining_today', 0) > 0 and status.get('enabled'):
                do_ads(api, args.max_ads)

        # Refresh user
        user = api.me()
        print_user(user)

    if args.loop:
        print(f"🔄 Loop mode: interval={args.interval}s")
        while True:
            try:
                run_once()
            except Exception as e:
                print(f"❌ Error: {e}")
            print(f"\n💤 Sleeping {args.interval}s...")
            time.sleep(args.interval)
    else:
        run_once()


if __name__ == '__main__':
    main()
