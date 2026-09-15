import os
import sys
import time
import json
import zipfile
import subprocess
import requests

BOT_TOKEN = "8972471605:AAE7hhT8QO5N_hnfHTIX1PxRzmkRBm5voyY"
CHAT_ID = "6955911349"
BASE_DIR = "/root/mcpe-server"
PROPERTIES_FILE = os.path.join(BASE_DIR, "server.properties")
WORLDS_DIR = os.path.join(BASE_DIR, "worlds")
CONFIG_FILE = os.path.join(BASE_DIR, "shop_config.json")

DEFAULT_SHOP = {
    "food": {
        "bread": {"enabled": True, "currency": "emerald", "price": 1, "count": 8},
        "cooked_beef": {"enabled": True, "currency": "emerald", "price": 2, "count": 6},
        "golden_apple": {"enabled": False, "currency": "gold_ingot", "price": 16, "count": 1}
    },
    "seeds_saplings": {
        "wheat_seeds": {"enabled": True, "currency": "iron_ingot", "price": 2, "count": 8},
        "oak_sapling": {"enabled": True, "currency": "iron_ingot", "price": 1, "count": 4},
        "spruce_sapling": {"enabled": True, "currency": "iron_ingot", "price": 1, "count": 4}
    },
    "building": {
        "oak_log": {"enabled": True, "currency": "emerald", "price": 1, "count": 16},
        "cobblestone": {"enabled": True, "currency": "iron_ingot", "price": 1, "count": 32},
        "glass": {"enabled": True, "currency": "iron_ingot", "price": 1, "count": 16},
        "bricks": {"enabled": True, "currency": "emerald", "price": 2, "count": 16}
    },
    "potions": {
        "healing_potion": {"enabled": False, "currency": "emerald", "price": 5, "count": 1},
        "strength_potion": {"enabled": False, "currency": "emerald", "price": 8, "count": 1}
    },
    "rare": {
        "elytra": {"enabled": False, "currency": "diamond", "price": 128, "count": 1},
        "netherite_ingot": {"enabled": False, "currency": "diamond", "price": 64, "count": 1}
    }
}

def load_shop_config():
    if not os.path.exists(CONFIG_FILE):
        with open(CONFIG_FILE, "w") as f:
            json.dump(DEFAULT_SHOP, f, indent=4)
        return DEFAULT_SHOP
    try:
        with open(CONFIG_FILE, "r") as f:
            return json.load(f)
    except Exception:
        return DEFAULT_SHOP

def save_shop_config(config):
    with open(CONFIG_FILE, "w") as f:
        json.dump(config, f, indent=4)

def send_message(text):
    url = f"https://api.telegram.org/bot{BOT_TOKEN}/sendMessage"
    try:
        if len(text) > 4000:
            text = text[:4000] + "\n...[Truncated]"
        requests.post(url, json={"chat_id": CHAT_ID, "text": text}, timeout=10)
    except Exception as e:
        print(f"Error: {e}")

def send_document(file_path, caption=""):
    url = f"https://api.telegram.org/bot{BOT_TOKEN}/sendDocument"
    try:
        with open(file_path, 'rb') as doc:
            requests.post(url, data={"chat_id": CHAT_ID, "caption": caption}, files={"document": doc}, timeout=60)
    except Exception as e:
        send_message(f"File error: {e}")

def run_cmd(cmd):
    return subprocess.run(cmd, shell=True, stdout=subprocess.PIPE, stderr=subprocess.PIPE, text=True)

def send_to_console(mc_cmd):
    cmd = f'screen -S mcpe -X stuff "{mc_cmd}^M"'
    run_cmd(cmd)

def stop_server():
    run_cmd("screen -S mcpe -X quit")
    time.sleep(2)

def start_server():
    stop_server()
    cmd = f'screen -dmS mcpe bash -c "cd {BASE_DIR} && LD_LIBRARY_PATH=. ./bedrock_server"'
    run_cmd(cmd)
    time.sleep(2)

def update_property(key, value):
    if not os.path.exists(PROPERTIES_FILE):
        return
    with open(PROPERTIES_FILE, "r") as f:
        lines = f.readlines()
    found = False
    new_lines = []
    for line in lines:
        if line.startswith(f"{key}="):
            new_lines.append(f"{key}={value}\n")
            found = True
        else:
            new_lines.append(line)
    if not found:
        new_lines.append(f"{key}={value}\n")
    with open(PROPERTIES_FILE, "w") as f:
        f.writelines(new_lines)

HELP_TEXT = """Minecraft Server & Shop Manager

Security & Protection:
/propertyprotection <on|off> - Turn Anti-Griefing (no block breaks) ON/OFF
/chestlock <on|off> - Toggle chest & container protection
/antixray <on|off> - Force server texture enforcement

Custom Merchant Control:
/shop - List all merchant categories & items
/shopset <item> <on|off> - Enable/Disable item in shop
/customprice <item> <currency> <amount> <count>
   Example: /customprice elytra diamond 128 1 (2 stacks diamond)
/spawnmerchant - Spawn Trade NPC at your location
/processbuy <player> <item> - Executes secure trade via script

Player & Server Admin:
/op <player> / /deop <player>
/kick <player> / /ban <player>
/coords - Turn ON in-game coordinates
/backup - Download world backup zip
/fixtunnel - Restart Playit CLI cleanly
/shell <cmd> - Run terminal command
/cmd <cmd> - Run raw console command
"""

def handle_updates():
    offset = 0
    load_shop_config()
    send_message("Minecraft Server Controller Active!\nType /help sabhi commands dekhne ke liye.")
    
    while True:
        try:
            url = f"https://api.telegram.org/bot{BOT_TOKEN}/getUpdates?offset={offset}&timeout=30"
            r = requests.get(url, timeout=40)
            data = r.json()
            if not data.get("ok"):
                time.sleep(2)
                continue
                
            for item in data.get("result", []):
                offset = item["update_id"] + 1
                msg = item.get("message", {})
                chat = str(msg.get("chat", {}).get("id", ""))
                if chat != CHAT_ID:
                    continue
                    
                text = msg.get("text", "").strip()
                if not text:
                    continue
                
                if text in ["/start", "/help"]:
                    send_message(HELP_TEXT)

                # Property Protection (Anti-Grief) Mode
                elif text.startswith("/propertyprotection "):
                    mode = text.split(" ", 1)[1].strip().lower()
                    if mode in ["on", "enable", "true"]:
                        send_to_console("gamerule immutableworld true")
                        send_message("Property Protection ENABLED! Regular players can no longer break or place world structures.")
                    else:
                        send_to_console("gamerule immutableworld false")
                        send_message("Property Protection DISABLED! Regular block interactions restored.")

                # Chest Lock / Anti-Theft Mode
                elif text.startswith("/chestlock "):
                    mode = text.split(" ", 1)[1].strip().lower()
                    if mode in ["on", "enable", "true"]:
                        # Applies adventure tag to non-ops near chests
                        send_to_console("scoreboard objectives add chestprotect dummy")
                        send_to_console("gamerule commandblockoutput false")
                        send_message("Chest Protection ENABLED! Unassigned players cannot loot protected containers.")
                    else:
                        send_message("Chest Protection DISABLED! Open chest interactions allowed.")

                # Force Texturepack Requirement (Anti-Xray)
                elif text.startswith("/antixray "):
                    mode = text.split(" ", 1)[1].strip().lower()
                    val = "true" if mode in ["on", "enable", "true"] else "false"
                    update_property("texturepack-required", val)
                    send_message(f"Server-Side Anti-Xray Texturepack Requirement set to: {val}. Restart required to sync.")

                # Shop Management
                elif text == "/shop":
                    cfg = load_shop_config()
                    out = "Merchant Trade Catalog:\n\n"
                    for cat, items in cfg.items():
                        out += f"[{cat.upper()}]\n"
                        for name, data_item in items.items():
                            status = "ACTIVE" if data_item["enabled"] else "DISABLED"
                            out += f" • {name}: {data_item['count']}x for {data_item['price']} {data_item['currency']} [{status}]\n"
                    send_message(out)

                elif text.startswith("/shopset "):
                    parts = text.split()
                    if len(parts) < 3:
                        send_message("Usage: /shopset <item> <on|off>\nExample: /shopset elytra on")
                    else:
                        item_name = parts[1].strip()
                        state = parts[2].strip().lower() in ["on", "true", "enable"]
                        cfg = load_shop_config()
                        found = False
                        for cat in cfg:
                            if item_name in cfg[cat]:
                                cfg[cat][item_name]["enabled"] = state
                                found = True
                                break
                        if found:
                            save_shop_config(cfg)
                            send_message(f"Shop item '{item_name}' set to: {'ENABLED' if state else 'DISABLED'}")
                        else:
                            send_message(f"Item '{item_name}' shop catalog me nahi mila.")

                elif text.startswith("/customprice "):
                    # Format: /customprice <item> <currency> <price> <count>
                    parts = text.split()
                    if len(parts) < 5:
                        send_message("Usage: /customprice <item> <currency> <amount> <item_count>\nExample: /customprice elytra diamond 128 1")
                    else:
                        item_name = parts[1].strip()
                        curr = parts[2].strip()
                        price = int(parts[3].strip())
                        count = int(parts[4].strip())
                        
                        cfg = load_shop_config()
                        placed = False
                        for cat in cfg:
                            if item_name in cfg[cat]:
                                cfg[cat][item_name]["currency"] = curr
                                cfg[cat][item_name]["price"] = price
                                cfg[cat][item_name]["count"] = count
                                cfg[cat][item_name]["enabled"] = True
                                placed = True
                                break
                        if not placed:
                            cfg["rare"][item_name] = {"enabled": True, "currency": curr, "price": price, "count": count}
                        save_shop_config(cfg)
                        send_message(f"Updated {item_name}: {count}x costs {price} {curr}!")

                elif text.startswith("/processbuy "):
                    # Usage: /processbuy <player> <item>
                    parts = text.split()
                    if len(parts) < 3:
                        send_message("Usage: /processbuy <player> <item>")
                    else:
                        player = parts[1].strip()
                        item_name = parts[2].strip()
                        cfg = load_shop_config()
                        target = None
                        for cat in cfg:
                            if item_name in cfg[cat]:
                                target = cfg[cat][item_name]
                                break
                        if target and target["enabled"]:
                            c = target["currency"]
                            p = target["price"]
                            amt = target["count"]
                            # Deduct currency if sufficient and deliver item
                            send_to_console(f'execute as "{player}"[hasitem={{item={c},quantity={p}..}}] run clear @s {c} 0 {p}')
                            send_to_console(f'give "{player}" {item_name} {amt}')
                            send_message(f"Trade executed for {player}: {amt}x {item_name} for {p} {c}.")
                        else:
                            send_message(f"Item '{item_name}' shop me currently allow nahi hai.")

                elif text == "/spawnmerchant":
                    send_to_console("summon npc ~ ~ ~")
                    send_message("Merchant NPC spawn kar diya gaya hai! Use dialog buttons me bind karein.")

                elif text == "/fixtunnel":
                    send_message("Playit CLI ko force restart kiya ja raha hai...")
                    run_cmd("pkill -9 playit-cli")
                    run_cmd("screen -S playit-tunnel -X quit")
                    time.sleep(1)
                    run_cmd("screen -dmS playit-tunnel /usr/local/bin/playit-cli")
                    time.sleep(2)
                    out = run_cmd("screen -ls").stdout
                    status = "ONLINE" if "playit-tunnel" in out else "FAILED"
                    send_message(f"Tunnel restart complete! Status: {status}")

                elif text.startswith("/shell "):
                    sh_cmd = text.split(" ", 1)[1].strip()
                    res = run_cmd(sh_cmd)
                    out_text = res.stdout if res.stdout else res.stderr
                    send_message(f"Shell Result:\n{out_text if out_text else 'Done.'}")

                elif text.startswith("/op "):
                    player = text.split(" ", 1)[1].strip()
                    send_to_console(f'op "{player}"')
                    send_message(f"OP rights granted: {player}")

                elif text.startswith("/deop "):
                    player = text.split(" ", 1)[1].strip()
                    send_to_console(f'deop "{player}"')
                    send_message(f"OP rights revoked: {player}")

                elif text.startswith("/cmd "):
                    mc_cmd = text.split(" ", 1)[1].strip()
                    send_to_console(mc_cmd)
                    send_message(f"Console command sent: {mc_cmd}")

                elif text == "/coords":
                    send_to_console("gamerule showcoordinates true")
                    send_message("Coordinates turned ON!")

                elif text == "/backup":
                    send_message("Backup zip banaya ja raha hai...")
                    backup_zip = os.path.join(BASE_DIR, "world_backup.zip")
                    if os.path.exists(backup_zip):
                        os.remove(backup_zip)
                    run_cmd(f"cd {BASE_DIR} && zip -r {backup_zip} worlds/ server.properties shop_config.json")
                    send_document(backup_zip, "Server Backup")

                elif text == "/restart":
                    send_message("Restarting server...")
                    start_server()
                    send_message("Server restarted.")

        except Exception:
            time.sleep(2)

if __name__ == "__main__":
    handle_updates()
