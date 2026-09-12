import re

with open('handlers.py', 'r', encoding='utf-8') as f:
    content = f.read()

# 1. Add USERS_FILE and related functions
auth_code_addition = """
USERS_FILE = DATA_DIR / "allowed_users.json"

def _ensure_data_file():
    \"\"\"Ensures data directory and json files exist.\"\"\"
    DATA_DIR.mkdir(parents=True, exist_ok=True)
    if not GROUPS_FILE.exists():
        try:
            with open(GROUPS_FILE, "w", encoding="utf-8") as f:
                json.dump([], f)
        except Exception as e:
            logger.error(f"Failed to create groups file: {e}")
    if not USERS_FILE.exists():
        try:
            with open(USERS_FILE, "w", encoding="utf-8") as f:
                json.dump([], f)
        except Exception as e:
            logger.error(f"Failed to create users file: {e}")

def get_allowed_users() -> list:
    _ensure_data_file()
    try:
        with open(USERS_FILE, "r", encoding="utf-8") as f:
            return json.load(f)
    except Exception as e:
        logger.error(f"Error reading allowed users: {e}")
        return []

def is_user_allowed(user_id: int) -> bool:
    return str(user_id) in [str(u) for u in get_allowed_users()]

def add_allowed_user(user_id: int):
    users = get_allowed_users()
    if str(user_id) not in [str(u) for u in users]:
        users.append(str(user_id))
        with open(USERS_FILE, "w", encoding="utf-8") as f:
            json.dump(users, f)

def remove_allowed_user(user_id: int):
    users = get_allowed_users()
    users = [str(u) for u in users if str(u) != str(user_id)]
    with open(USERS_FILE, "w", encoding="utf-8") as f:
        json.dump(users, f)
"""

# Replace the old _ensure_data_file block
old_ensure_data_file = """def _ensure_data_file():
    \"\"\"Ensures data directory and allowed_groups.json exist.\"\"\"
    DATA_DIR.mkdir(parents=True, exist_ok=True)
    if not GROUPS_FILE.exists():
        try:
            with open(GROUPS_FILE, "w", encoding="utf-8") as f:
                json.dump([], f)
        except Exception as e:
            logger.error(f"Failed to create groups file: {e}")"""
            
if old_ensure_data_file in content:
    content = content.replace(old_ensure_data_file, auth_code_addition)
else:
    print("Warning: _ensure_data_file not found")

# 2. Update UNAUTHORIZED_DM_MESSAGE
old_unauth = """UNAUTHORIZED_DM_MESSAGE = (
    "👋 Hey there!\\n\\n"
    "⛔ You're not an authorized user to use this bot.\\n\\n"
    "📩 Contact @uzumaki289 to get access to the bot!\\n\\n"
    "Thank you! 😊"
)"""
new_unauth = """UNAUTHORIZED_DM_MESSAGE = (
    "👋 Hey there!\\n\\n"
    "⛔ You're not an authorized user to use this bot.\\n\\n"
    "👇 Click /request to send an access request to the admin.\\n\\n"
    "📩 For any other issues, contact @uzumaki289.\\n\\n"
    "Thank you! 😊"
)"""
content = content.replace(old_unauth, new_unauth)

# 3. Add request_command
request_command_code = """
async def request_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    \"\"\"Handles the /request command for unauthorized users to request access.\"\"\"
    user = update.effective_user
    user_id = user.id
    
    if is_admin(user_id) or is_user_allowed(user_id):
        await update.message.reply_text("✅ You are already authorized to use this bot!")
        return

    admin_ids = [aid.strip() for aid in str(ADMIN_USER_ID).split(",") if aid.strip()]
    if not admin_ids:
        await update.message.reply_text("❌ No admin is configured to receive requests.")
        return

    # Notify user
    await update.message.reply_text("✅ Your access request has been sent to the admin. You will be notified when it's approved.")
    
    # Notify admin
    keyboard = [
        [
            InlineKeyboardButton("✅ Approve", callback_data=f"approve_user:{user_id}"),
            InlineKeyboardButton("❌ Decline", callback_data=f"decline_user:{user_id}")
        ]
    ]
    reply_markup = InlineKeyboardMarkup(keyboard)
    
    admin_msg = (
        f"🔔 **New Access Request**\\n\\n"
        f"👤 **Name:** {user.full_name}\\n"
        f"🔗 **Username:** @{user.username if user.username else 'N/A'}\\n"
        f"🆔 **User ID:** `{user_id}`\\n\\n"
        f"Do you want to approve this user?"
    )
    
    for aid in admin_ids:
        try:
            await context.bot.send_message(
                chat_id=aid, 
                text=admin_msg, 
                reply_markup=reply_markup,
                parse_mode=constants.ParseMode.MARKDOWN
            )
        except Exception as e:
            logger.error(f"Failed to send request to admin {aid}: {e}")
"""

# Insert request_command before help_command
content = content.replace("async def help_command", request_command_code + "\nasync def help_command")

# 4. Update access checks from `not is_admin(user_id)` to `not is_admin(user_id) and not is_user_allowed(user_id)`
# We only want to do this for download commands (start, handle_message, handle_document, callback_query).
# We DO NOT want to do it for `/restart`, `/setcookie`, etc.
def replace_auth(func_name, code):
    pattern = f"(async def {func_name}.*?if chat\\.type == \"private\" and not is_admin\\(user_id\\):)"
    replacement = r"async def \1\n    if chat.type == \"private\" and not is_admin(user_id) and not is_user_allowed(user_id):"
    # Actually simpler: find the exact line in those specific functions
    pass

# For start_command
content = content.replace(
    "if chat.type == \"private\" and not is_admin(user.id):",
    "if chat.type == \"private\" and not is_admin(user.id) and not is_user_allowed(user.id):"
)

# For handle_message
content = content.replace(
    "if not is_group and not is_admin(user_id):",
    "if not is_group and not is_admin(user_id) and not is_user_allowed(user_id):"
)

# 5. Handle Callback Query for approve/decline
callback_addition = """
    if action == "approve_user":
        target_id = parts[1]
        add_allowed_user(target_id)
        await query.answer(f"✅ User {target_id} approved!", show_alert=True)
        await query.edit_message_text(f"{query.message.text}\\n\\n✅ **APPROVED**")
        try:
            await context.bot.send_message(chat_id=target_id, text="🎉 **Good news!**\\nYour access request has been approved by the admin. You can now use the bot! Send /start to begin.", parse_mode=constants.ParseMode.MARKDOWN)
        except:
            pass
        return

    if action == "decline_user":
        target_id = parts[1]
        await query.answer(f"❌ User {target_id} declined.", show_alert=True)
        await query.edit_message_text(f"{query.message.text}\\n\\n❌ **DECLINED**")
        try:
            await context.bot.send_message(chat_id=target_id, text="❌ **Update:**\\nYour access request was declined by the admin.", parse_mode=constants.ParseMode.MARKDOWN)
        except:
            pass
        return
"""
content = content.replace(
    "if action == \"stop\":",
    callback_addition.strip() + "\n\n    if action == \"stop\":"
)

# 6. Add to register_handlers
content = content.replace(
    "application.add_handler(CommandHandler(\"start\", start_command))",
    "application.add_handler(CommandHandler(\"start\", start_command))\n    application.add_handler(CommandHandler(\"request\", request_command))"
)

with open('handlers_updated.py', 'w', encoding='utf-8') as f:
    f.write(content)
print("Updated handlers_updated.py")
