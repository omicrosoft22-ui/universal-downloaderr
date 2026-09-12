import re

with open('handlers.py', 'r', encoding='utf-8') as f:
    content = f.read()

# 1. Add imports
import_statement = """
from terabox_downloader import (
    is_terabox_url,
    extract_terabox_info,
    download_terabox_media,
    get_terabox_api_key,
    set_terabox_api_key
)
"""
content = re.sub(r'from mtproto_uploader', import_statement.strip() + '\nfrom mtproto_uploader', content)

# 2. Add /api command function right before def register_handlers
api_cmd_func = """
async def api_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if not is_admin(update.effective_user.id):
        await update.message.reply_text("⛔️ Only admins can use this command.")
        return
        
    if not context.args:
        current_key = get_terabox_api_key()
        await update.message.reply_text(f"ℹ️ **Current TeraBox API Key:**\\n`{current_key}`\\n\\nTo change it, use:\\n`/api <new_key>`", parse_mode=constants.ParseMode.MARKDOWN)
        return
        
    new_key = context.args[0]
    set_terabox_api_key(new_key)
    await update.message.reply_text(f"✅ **TeraBox API Key updated successfully!**\\nNew Key: `{new_key}`", parse_mode=constants.ParseMode.MARKDOWN)

"""
content = re.sub(r'def register_handlers\(application\):', api_cmd_func + 'def register_handlers(application):', content)

# 3. Add to register_handlers
content = re.sub(r'application.add_handler\(CommandHandler\("startgc", startgc_command\)\)', r'application.add_handler(CommandHandler("startgc", startgc_command))\n    application.add_handler(CommandHandler("api", api_command))', content)

# 4. Add routing back to extract
content = re.sub(r'    if is_youtube_url', r'    if is_terabox_url(url):\n        return await extract_terabox_info(url)\n    elif is_youtube_url', content, count=1)

# 5. Add routing back to download
content = re.sub(r'    if is_youtube_url', r'    if is_terabox_url(url):\n        return await download_terabox_media(url, quality=quality, format_selector=format_selector)\n    elif is_youtube_url', content, count=1)

with open('handlers.py', 'w', encoding='utf-8') as f:
    f.write(content)

print("handlers.py successfully updated!")
