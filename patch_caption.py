import re

with open('handlers.py', 'r', encoding='utf-8') as f:
    content = f.read()

# 1. Update caption
old_caption = '    caption = f"🎬 **{title}**\\n{platform_badge}" if is_audio else f"🎬 **{title}**\\n{platform_badge}"'
new_caption = '    caption = f"🎬 **{title}**\\n{platform_badge}\\n\\n🔗 `{url}`"'
content = content.replace(old_caption, new_caption)

# 2. Add message deletion in handle_message
# find send_media_to_chat block in handle_message (not the query callback)
handle_message_block = """                    await send_media_to_chat(
                        bot=context.bot,
                        chat_id=update.effective_chat.id,
                        file_path=downloaded_file,
                        title=title,
                        uploader=uploader,
                        duration_sec=duration_sec,
                        url=url,
                        quality="720",
                        info=dl_info or info,
                        progress_status_updater=lambda txt: edit_status_msg_safe(status_msg, txt),
                    )"""

delete_code = """
                    # Delete the original message containing the link
                    try:
                        if update.message:
                            await update.message.delete()
                    except Exception:
                        pass
"""

content = content.replace(handle_message_block, handle_message_block + delete_code)

with open('handlers.py', 'w', encoding='utf-8') as f:
    f.write(content)
print("Updated handlers.py")
