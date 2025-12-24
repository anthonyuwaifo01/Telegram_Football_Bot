import os
import json
import random
from telegram import Update
from telegram.ext import Application, CommandHandler, MessageHandler, filters, ContextTypes
from telegram.constants import ParseMode

DATA_FILE = "players.json"
PLAYERS_PER_TEAM = 6

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
    try:
        if os.path.exists(DATA_FILE):
            with open(DATA_FILE, "r") as f:
                return json.load(f)
        else:
            return init_data()
    except Exception as e:
        print(f"Error loading data: {e}")
        return init_data()

def save_data(data):
    try:
        with open(DATA_FILE, "w") as f:
            json.dump(data, f, indent=2)
    except Exception as e:
        print(f"Error saving data: {e}")

def is_admin(user_id, data):
    return user_id in data.get("admins", [])

def create_teams(players):
    num_players = len(players)
    if num_players == 0:
        return []
    shuffled = players.copy()
    random.shuffle(shuffled)
    teams = []
    for i in range(0, num_players, PLAYERS_PER_TEAM):
        team = shuffled[i:i+PLAYERS_PER_TEAM]
        teams.append(team)
    return teams

def format_teams(teams):
    team_emojis = ["🔴", "🔵", "🟢", "🟡", "🟣", "🟠", "⚫", "⚪"]
    team_names = ["Red", "Blue", "Green", "Yellow", "Purple", "Orange", "Black", "White"]
    text = "⚽ <b>THIS WEEK'S TEAMS</b> ⚽\n"
    text += "═" * 30 + "\n\n"
    for i, team in enumerate(teams):
        if not team:
            continue
        emoji = team_emojis[i % len(team_emojis)]
        name = team_names[i % len(team_names)]
        text += f"{emoji} <b>{name} Team</b> ({len(team)} players)\n"
        for p in team:
            username = f"@{p['username']}" if p.get('username') else p['name']
            text += f"  • {username}\n"
        text += "\n"
    return text

async def start_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = update.effective_user.id
    data = load_data()
    welcome_text = (
        "⚽ <b>Welcome to Football Team Bot!</b> ⚽\n\n"
        "<b>How it works:</b>\n"
        "1️⃣ Admin starts weekly selection with /begin\n"
        "2️⃣ Players reply 'in' or 'out'\n"
        "3️⃣ Admin creates teams with /end\n\n"
        "<b>Available Commands:</b>\n"
        "• /help - Show all commands\n"
        "• /addme - Become first admin\n\n"
    )
    if is_admin(user_id, data):
        welcome_text += "✅ You are an admin!"
    else:
        welcome_text += "👤 You are a player"
    await update.message.reply_text(welcome_text, parse_mode=ParseMode.HTML)

async def help_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = update.effective_user.id
    data = load_data()
    help_text = "⚽ <b>FOOTBALL BOT COMMANDS</b>\n\n"
    help_text += "<b>Everyone:</b>\n"
    help_text += "• in - Join this week\n"
    help_text += "• out - Skip this week\n"
    help_text += "• /help - Show this message\n\n"
    if is_admin(user_id, data):
        help_text += "<b>Admin Only:</b>\n"
        help_text += "• /begin - Start selection\n"
        help_text += "• /end - Create random teams\n"
        help_text += "• /status - View current status\n"
        help_text += "• /reset - Reset session\n"
        help_text += "• /addadmin - Reply to message to add admin\n"
        help_text += "• /removeadmin - Reply to message to remove admin\n"
        help_text += "• /listadmins - Show all admins"
    await update.message.reply_text(help_text, parse_mode=ParseMode.HTML)

async def addme_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = update.effective_user.id
    user_name = update.effective_user.first_name
    data = load_data()
    if len(data["admins"]) == 0:
        data["admins"].append(user_id)
        save_data(data)
        await update.message.reply_text(f"👑 {user_name}, you are now the first admin!")
    elif is_admin(user_id, data):
        await update.message.reply_text("✅ You're already an admin!")
    else:
        await update.message.reply_text("❌ Only existing admins can add new admins using /addadmin")

async def addadmin_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = update.effective_user.id
    data = load_data()
    if not is_admin(user_id, data):
        await update.message.reply_text("❌ Only admins can add other admins")
        return
    if update.message.reply_to_message:
        new_admin_id = update.message.reply_to_message.from_user.id
        new_admin_name = update.message.reply_to_message.from_user.first_name
        if new_admin_id not in data["admins"]:
            data["admins"].append(new_admin_id)
            save_data(data)
            await update.message.reply_text(f"✅ {new_admin_name} is now an admin!\nTotal admins: {len(data['admins'])}")
        else:
            await update.message.reply_text(f"ℹ️ {new_admin_name} is already an admin")
    else:
        await update.message.reply_text("💡 Reply to someone's message with /addadmin to make them an admin")

async def removeadmin_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = update.effective_user.id
    data = load_data()
    if not is_admin(user_id, data):
        await update.message.reply_text("❌ Only admins can remove other admins")
        return
    if update.message.reply_to_message:
        remove_admin_id = update.message.reply_to_message.from_user.id
        remove_admin_name = update.message.reply_to_message.from_user.first_name
        if remove_admin_id in data["admins"]:
            data["admins"].remove(remove_admin_id)
            save_data(data)
            await update.message.reply_text(f"✅ {remove_admin_name} is no longer an admin\nRemaining admins: {len(data['admins'])}")
        else:
            await update.message.reply_text(f"ℹ️ {remove_admin_name} is not an admin")
    else:
        await update.message.reply_text("💡 Reply to someone's message with /removeadmin to remove their admin status")

async def listadmins_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    data = load_data()
    if len(data["admins"]) == 0:
        await update.message.reply_text("No admins yet. Use /addme to become the first admin!")
    else:
        admin_list = "👑 <b>Current Admins:</b>\n\n"
        for admin_id in data["admins"]:
            try:
                admin = await context.bot.get_chat(admin_id)
                name = admin.first_name
                username = f"@{admin.username}" if admin.username else ""
                admin_list += f"• {name} {username}\n"
            except:
                admin_list += f"• User ID: {admin_id}\n"
        await update.message.reply_text(admin_list, parse_mode=ParseMode.HTML)

async def begin_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = update.effective_user.id
    chat_id = update.effective_chat.id
    data = load_data()
    if not is_admin(user_id, data):
        await update.message.reply_text("❌ Only admins can start selection")
        return
    data["session"]["active"] = True
    data["session"]["participants"] = []
    data["session"]["chat_id"] = chat_id
    save_data(data)
    message = ("🎮 <b>TEAM SELECTION STARTED!</b>\n\n"
               "Reply with:\n"
               "• <b>in</b> - Join this week\n"
               "• <b>out</b> - Skip this week\n\n"
               "Admin will announce teams later!")
    await update.message.reply_text(message, parse_mode=ParseMode.HTML)

async def end_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = update.effective_user.id
    data = load_data()
    if not is_admin(user_id, data):
        await update.message.reply_text("❌ Only admins can end selection")
        return
    if not data["session"]["active"]:
        await update.message.reply_text("❌ No active session. Use /begin first")
        return
    participants = data["session"]["participants"]
    if not participants:
        await update.message.reply_text("❌ No players have joined yet!")
        return
    player_list = []
    for user_id in participants:
        player_info = data["players"].get(str(user_id), {"name": "Unknown", "username": None})
        player_list.append(player_info)
    teams = create_teams(player_list)
    result = f"🎲 <b>RANDOM TEAM SELECTION</b>\n\n{format_teams(teams)}"
    result += f"<b>Total Players:</b> {len(player_list)}\n"
    result += f"<b>Teams Created:</b> {len(teams)}"
    await update.message.reply_text(result, parse_mode=ParseMode.HTML)
    data["session"]["active"] = False
    save_data(data)

async def status_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = update.effective_user.id
    data = load_data()
    if not is_admin(user_id, data):
        await update.message.reply_text("❌ Admin only command")
        return
    session = data["session"]
    status = "🟢 ACTIVE" if session["active"] else "🔴 INACTIVE"
    participant_count = len(session["participants"])
    status_msg = f"📊 <b>SESSION STATUS</b>\n\n"
    status_msg += f"<b>Status:</b> {status}\n"
    status_msg += f"<b>Players In:</b> {participant_count}\n\n"
    if participant_count > 0:
        status_msg += "<b>Participants:</b>\n"
        for user_id in session["participants"]:
            player = data["players"].get(str(user_id), {"name": "Unknown", "username": None})
            username = f"@{player['username']}" if player.get('username') else player['name']
            status_msg += f"  • {username}\n"
    await update.message.reply_text(status_msg, parse_mode=ParseMode.HTML)

async def reset_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = update.effective_user.id
    data = load_data()
    if not is_admin(user_id, data):
        await update.message.reply_text("❌ Only admins can reset")
        return
    data["session"]["active"] = False
    data["session"]["participants"] = []
    save_data(data)
    await update.message.reply_text("🔄 Session reset. Use /begin to start new selection")

async def handle_message(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = update.effective_user.id
    user_name = update.effective_user.first_name
    username = update.effective_user.username
    chat_id = update.effective_chat.id
    message_text = update.message.text.lower().strip()
    data = load_data()
    if data["session"]["active"] and data["session"]["chat_id"] != chat_id:
        return
    if message_text == "in":
        if not data["session"]["active"]:
            await update.message.reply_text("❌ No active selection. Wait for admin to /begin")
            return
        if str(user_id) not in data["players"]:
            data["players"][str(user_id)] = {"name": user_name, "username": username}
        if user_id not in data["session"]["participants"]:
            data["session"]["participants"].append(user_id)
            save_data(data)
            display_name = f"@{username}" if username else user_name
            await update.message.reply_text(f"✅ {display_name} is IN!\nCurrent count: {len(data['session']['participants'])} players")
        else:
            await update.message.reply_text(f"ℹ️ You're already in!")
    elif message_text == "out":
        if not data["session"]["active"]:
            await update.message.reply_text("❌ No active selection")
            return
        if user_id in data["session"]["participants"]:
            data["session"]["participants"].remove(user_id)
            save_data(data)
            display_name = f"@{username}" if username else user_name
            await update.message.reply_text(f"❌ {display_name} is OUT\nCurrent count: {len(data['session']['participants'])} players")
        else:
            await update.message.reply_text("ℹ️ You weren't in the list")

def main():
    TOKEN = os.environ.get("TELEGRAM_BOT_TOKEN")
    if not TOKEN:
        print("ERROR: TELEGRAM_BOT_TOKEN environment variable not set!")
        return
    
    application = Application.builder().token(TOKEN).build()
    
    # Register commands
    application.add_handler(CommandHandler("start", start_command))
    application.add_handler(CommandHandler("help", help_command))
    application.add_handler(CommandHandler("addme", addme_command))
    application.add_handler(CommandHandler("addadmin", addadmin_command))
    application.add_handler(CommandHandler("removeadmin", removeadmin_command))
    application.add_handler(CommandHandler("listadmins", listadmins_command))
    application.add_handler(CommandHandler("begin", begin_command))
    application.add_handler(CommandHandler("end", end_command))
    application.add_handler(CommandHandler("status", status_command))
    application.add_handler(CommandHandler("reset", reset_command))
    application.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, handle_message))
    
    print("Bot started successfully!")
    
    # Start polling with proper configuration
    application.run_polling(
        drop_pending_updates=True,
        allowed_updates=Update.ALL_TYPES
    )

if __name__ == "__main__":
    main()
