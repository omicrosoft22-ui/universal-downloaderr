with open('terabox_downloader.py', 'r', encoding='utf-8') as f:
    code = f.read()

with open('patch_teradown.py', 'r', encoding='utf-8') as f:
    patch = f.read()

patch_lines = patch.split('\n')[4:]
patch_code = '\n'.join(patch_lines)

parts = code.split('async def extract_terabox_info')
new_code = parts[0] + patch_code + '\n\nasync def extract_terabox_info' + parts[1]

old_logic = '''    # 1. Primary Engine (Cookie & Gateway Architecture)
    gw_success, gw_info, gw_err = await _resolve_via_gateway(url)
    if gw_success and gw_info:
        logger.info("TeraBox link resolved successfully via primary Cookie/Gateway engine.")
        return True, gw_info, None

    logger.info(f"Primary Cookie/Gateway resolver unavailable ({gw_err}). Engaging Hostinger backup resolver...")

    # 2. Backup Engine (Hostinger API)'''

new_logic = '''    # 1. Premium Engine (TeraDown API)
    td_success, td_info, td_err = await _resolve_via_teradown(url)
    if td_success and td_info:
        logger.info("TeraBox link resolved successfully via premium TeraDown API.")
        return True, td_info, None

    logger.info(f"Premium TeraDown API failed ({td_err}). Engaging Cookie/Gateway engine...")

    # 2. Backup Engine 1 (Cookie & Gateway Architecture)
    gw_success, gw_info, gw_err = await _resolve_via_gateway(url)
    if gw_success and gw_info:
        logger.info("TeraBox link resolved successfully via primary Cookie/Gateway engine.")
        return True, gw_info, None

    logger.info(f"Cookie/Gateway resolver unavailable ({gw_err}). Engaging Hostinger backup resolver...")

    # 3. Backup Engine 2 (Hostinger API)'''

if old_logic in new_code:
    new_code = new_code.replace(old_logic, new_logic)
    with open('terabox_downloader.py', 'w', encoding='utf-8') as f:
        f.write(new_code)
    print('SUCCESS')
else:
    print('OLD LOGIC NOT FOUND! Please check.')
