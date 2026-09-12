import re

with open('handlers.py', 'r', encoding='utf-8') as f:
    lines = f.readlines()

for i, line in enumerate(lines):
    if 'caption = f"' in line and '{title}' in line and '{platform_badge}' in line and 'is_audio' in line:
        lines[i] = '    caption = f"🎬 **{title}**\\n{platform_badge}\\n\\n🔗 `{url}`"\n'
        print('Found and replaced!')
        break

with open('handlers.py', 'w', encoding='utf-8') as f:
    f.writelines(lines)
