import os
import json
import random
import threading
from http.server import HTTPServer, BaseHTTPRequestHandler

from telegram import Update
from telegram.ext import (
    Application,
    CommandHandler,
    MessageHandler,
    ContextTypes,
    filters
)
from telegram.constants import ParseMode


# =====================
# CONFIG
# =====================
DATA_FILE = "players.json"
PLAYERS_PER_TEAM = 6


# =====================
# HEALTH CHECK SERVER (REQUIRED FOR RENDER FREE)
# =====================
def run_http_server():
    port = int(os.environ.get("PORT", 10000))

    class HealthHandler(BaseHTTPRequestHandler):
        def do_GET(self):
            self.send_response(200)
            self.send_header("Content-type", "text/plain")
            self.end_headers()
            self.wfile.write(b"OK")

        def log_message(self, format, *args):
            return  # silence logs

    server = HTTPServer(("0.0.0.0", port), HealthHandler)
    server.serve_forever()


# =====================
# DATA HELPERS
# =====================
def init_data():
    return {
        "admins": [],
        "players": {},
        "session": {
            "active": False,
            "participants": [],
            "chat_id": None
        }
    }


def load_data():
    if not os.path.exists(DATA_FILE):
        return init_data()
    try:
        with open(DATA_FILE, "r") as f:
            return json.load(f)
    except Exception:
        return init_data()


def save_data(data):
    with open(DATA_FILE, "w") as f:
        json.dump(data, f, indent=2)


def is_admin(user_id, data):
    return user_id in data.get("admins", [])


# =====================
# TEAM LOGIC
# =====================
def create_teams(players):
    random.shuffle(players)
    return [players[i:i + PLAYERS_PER_TEAM] for i in range(0, len(players), PLAYERS_PER_TEAM)]


def format_teams(teams):
    emojis = ["🔴", "🔵", "🟢", "🟡", "🟣", "🟠"]
    names = ["Red", "Blue", "Green", "Yellow", "Purple", "Orange"]

    text = "⚽ <b>THIS WEEK'S TEAMS</b> ⚽\n\n"
    for i, team in enumerate(teams):
        text += f"{emojis[i % len(emojis)]} <b>{names[i % len(names)]} Team</b>\n"
        for p in team:
            username = f"@{p['username']}" if p.get("username") else p["name"]
            text += f" • {username}\n"
        text += "\n"
    return text


# =====================
# COMMAND HANDLERS
# =====================
async def start_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text(
        "⚽ <b>Football Team Bot</b>\n\n"
        "Admin starts with /begin\n"
        "Players reply <b>in</b> or <b>out</b>\n"
        "Admin finishes with /end\n\n"
        "Use /addme to become first admin.",
        parse_mode=ParseMode.HTML
    )


async def help_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text(
        "<b>Commands</b>\n\n"
        "in / out – join or skip\n"
        "/begin – start session (admin)\n"
        "/end – generate teams (admin)\n"
        "/status – session status (admin)\n"
        "/reset – reset session (admin)\n"
        "/addme – become first admin",
        parse_mode=ParseMode.HTML
    )


async def addme_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    data = load_data()
    user_id = update.effective_user.id

    if not data["admins"]:
        data["admins"].append(user_id)
        save_data(data)
        await update.message.reply_text("👑 You are now the first admin!")
    else:
        await update.message.reply_text("❌ Admin already exists.")


async def begin_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    data = load_data()
    user_id = update.effective_user.id

    if not is_admin(user_id, data):
        await update.message.reply_text("❌ Admin only.")
        return

    data["session"] = {
        "active": True,
        "participants": [],
        "chat_id": update.effective_chat.id
    }
    save_data(data)

    await update.message.reply_text(
        "🎮 <b>Selection Started</b>\n\nReply with <b>in</b> or <b>out</b>",
        parse_mode=ParseMode.HTML
    )


async def end_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    data = load_data()
    user_id = update.effective_user.id

    if not is_admin(user_id, data):
        await update.message.reply_text("❌ Admin only.")
        return

    players = [
        data["players"][str(uid)]
        for uid in data["session"]["participants"]
    ]

    if not players:
        await update.message.reply_text("❌ No players joined.")
        return

    teams = create_teams(players)
    await update.message.reply_text(format_teams(teams), parse_mode=ParseMode.HTML)

    data["session"]["active"] = False
    save_data(data)


async def status_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    data = load_data()
    session = data["session"]

    await update.message.reply_text(
        f"Status: {'ACTIVE' if session['active'] else 'INACTIVE'}\n"
        f"Players: {len(session['participants'])}"
    )


async def reset_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    data = load_data()
    data["session"] = init_data()["session"]
    save_data(data)
    await update.message.reply_text("🔄 Session reset.")


async def handle_message(update: Update, context: ContextTypes.DEFAULT_TYPE):
    text = update.message.text.lower()
    user = update.effective_user
    data = load_data()

    if not data["session"]["active"]:
        return

    if str(user.id) not in data["players"]:
        data["players"][str(user.id)] = {
            "name": user.first_name,
            "username": user.username
        }

    if text == "in" and user.id not in data["session"]["participants"]:
        data["session"]["participants"].append(user.id)
        save_data(data)
        await update.message.reply_text("✅ You are IN!")

    elif text == "out" and user.id in data["session"]["participants"]:
        data["session"]["participants"].remove(user.id)
        save_data(data)
        await update.message.reply_text("❌ You are OUT.")


# =====================
# MAIN
# =====================
def main():
    token = os.environ.get("TELEGRAM_BOT_TOKEN")
    if not token:
        print("TELEGRAM_BOT_TOKEN not set")
        return

    print("Starting health server...")
    threading.Thread(target=run_http_server, daemon=True).start()

    print("Starting Telegram bot...")
    app = Application.builder().token(token).build()

    app.add_handler(CommandHandler("start", start_command))
    app.add_handler(CommandHandler("help", help_command))
    app.add_handler(CommandHandler("addme", addme_command))
    app.add_handler(CommandHandler("begin", begin_command))
    app.add_handler(CommandHandler("end", end_command))
    app.add_handler(CommandHandler("status", status_command))
    app.add_handler(CommandHandler("reset", reset_command))
    app.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, handle_message))

    app.run_polling(
    drop_pending_updates=True,
    allowed_updates=Update.ALL_TYPES,
    close_loop=False
)



if __name__ == "__main__":
    main()
