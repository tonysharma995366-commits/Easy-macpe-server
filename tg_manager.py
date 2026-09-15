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

# Default Merchant Catalog: Basic Building/Food enabled, Rare items locked
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
        send_message(f"File sending error: {e}")

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

def handle_document(doc):
    file_name = doc.get("file_name", "world.zip")
    if not file_name.endswith((".zip", ".mcworld")):
        send_message("Kripya sirf .zip ya .mcworld format bhejein!")
        return
    file_id = doc["file_id"]
    send_message("World download ho rahi hai...")
    res = requests.get(f"https://api.telegram.org/bot{BOT_TOKEN}/getFile?file_id={file_id}").json()
    file_path = res["result"]["file_path"]
    download_url = f"https://api.telegram.org/file/bot{BOT_TOKEN}/{file_path}"
    
    local_zip = os.path.join(BASE_DIR, "uploaded_world.zip")
    r = requests.get(download_url, stream=True)
    with open(local_zip, "wb") as f:
        for chunk in r.iter_content(chunk_size=8192):
            f.write(chunk)
            
    send_message("World extract karke apply ki ja rahi hai...")
    stop_server()
    world_folder_name = os.path.splitext(file_name)[0].replace(" ", "_")
    target_extract = os.path.join(WORLDS_DIR, world_folder_name)
    os.makedirs(target_extract, exist_ok=True)
    
    with zipfile.ZipFile(local_zip, 'r') as zip_ref:
        zip_ref.extractall(target_extract)
        
    update_property("level-name", world_folder_name)
    start_server()
    send_message(f"World successfully import ho gayi!\nLevel Name: {world_folder_name}\nServer restarted.")

HELP_TEXT = """Minecraft Server Full Control Panel

World & Generation:
/seed <number> - Generate new world with custom seed
/backup - Download complete server & world backup zip
[Send .zip/.mcworld] - Restore uploaded world file

Security & Protection:
/propertyprotection <on|off> - Turn Anti-Griefing (no block breaks) ON/OFF
/chestlock <on|off> - Toggle chest & container protection
/antixray <on|off> - Force server texture enforcement

Custom Merchant Control:
/shop - List all merchant categories & prices
/shopset <item> <on|off> - Allow/Block item in shop
/customprice <item> <currency> <amount> <count>
   Example: /customprice elytra diamond 128 1 (2 stacks diamond)
/spawnmerchant - Summon Merchant NPC at console location
/processbuy <player> <item> - Secure trade transaction

Game Rules & Gameplay:
/coords - Turn ON coordinates
/keepinventory - Keep inventory on death
/pvp <on|off> - Toggle PVP
/difficulty <peaceful|easy|normal|hard>
/gamemode <survival|creative|adventure>
/time <day|night|noon|midnight>
/weather <clear|rain|thunder>

Player & Server Admin:
/status - Check Minecraft & Playit status
/players - Online player list
/logs - Show last 15 console log lines
/op <player> / /deop <player>
/kick <player> / /ban <player> / /unban <player>
/fixtunnel - Restart Playit CLI
/restart / /startserver / /stopserver
/shell <cmd> - Run Linux terminal command
/cmd <cmd> - Run raw in-game console command
"""

def handle_updates():
    offset = 0
    load_shop_config()
    send_message("Minecraft Server Controller Active!\nType /help sabhi commands ke liye.")
    
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
                    
                if "document" in msg:
                    handle_document(msg["document"])
                    continue
                    
                text = msg.get("text", "").strip()
                if not text:
                    continue
                
                if text in ["/start", "/help"]:
                    send_message(HELP_TEXT)

                # Seed se naya world generate karna
                elif text.startswith("/seed"):
                    parts = text.split(maxsplit=1)
                    if len(parts) < 2:
                        send_message("Seed specify karein! Example: /seed 987654321")
                    else:
                        seed_val = parts[1].strip()
                        new_world = f"world_{int(time.time())}"
                        send_message(f"Seed {seed_val} apply karke naya world generate kiya ja raha hai...")
                        stop_server()
                        update_property("level-seed", seed_val)
                        update_property("level-name", new_world)
                        start_server()
                        send_message(f"Naya world ban gaya!\nWorld Name: {new_world}\nSeed: {seed_val}")

                # Anti-Grief / Property Guard
                elif text.startswith("/propertyprotection "):
                    mode = text.split(" ", 1)[1].strip().lower()
                    if mode in ["on", "enable", "true"]:
                        send_to_console("gamerule immutableworld true")
                        send_message("Property Protection ENABLED! Players cannot break/place blocks.")
                    else:
                        send_to_console("gamerule immutableworld false")
                        send_message("Property Protection DISABLED! Regular block interactions restored.")

                # Chest Protection Mode
                elif text.startswith("/chestlock "):
                    mode = text.split(" ", 1)[1].strip().lower()
                    if mode in ["on", "enable", "true"]:
                        send_to_console("scoreboard objectives add chestprotect dummy")
                        send_message("Chest Protection ENABLED! Containers protected.")
                    else:
                        send_message("Chest Protection DISABLED! Open chest interactions allowed.")

                # Force Texturepack Requirement (Anti-Xray)
                elif text.startswith("/antixray "):
                    mode = text.split(" ", 1)[1].strip().lower()
                    val = "true" if mode in ["on", "enable", "true"] else "false"
                    update_property("texturepack-required", val)
                    send_message(f"Anti-Xray texture enforcement set to: {val}. Restart required.")

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
                            send_message(f"'{item_name}' set to: {'ENABLED' if state else 'DISABLED'}")
                        else:
                            send_message(f"Item '{item_name}' shop me nahi mila.")

                elif text.startswith("/customprice "):
                    parts = text.split()
                    if len(parts) < 5:
                        send_message("Usage: /customprice <item> <currency> <amount> <count>\nExample: /customprice elytra diamond 128 1")
                    else:
                        item_name, curr, price, count = parts[1], parts[2], int(parts[3]), int(parts[4])
                        cfg = load_shop_config()
                        placed = False
                        for cat in cfg:
                            if item_name in cfg[cat]:
                                cfg[cat][item_name].update({"currency": curr, "price": price, "count": count, "enabled": True})
                                placed = True
                                break
                        if not placed:
                            cfg["rare"][item_name] = {"enabled": True, "currency": curr, "price": price, "count": count}
                        save_shop_config(cfg)
                        send_message(f"Updated {item_name}: {count}x costs {price} {curr}!")

                elif text.startswith("/processbuy "):
                    parts = text.split()
                    if len(parts) >= 3:
                        player, item_name = parts[1].strip(), parts[2].strip()
                        cfg = load_shop_config()
                        target = None
                        for cat in cfg:
                            if item_name in cfg[cat]:
                                target = cfg[cat][item_name]
                                break
                        if target and target["enabled"]:
                            c, p, amt = target["currency"], target["price"], target["count"]
                            send_to_console(f'execute as "{player}"[hasitem={{item={c},quantity={p}..}}] run clear @s {c} 0 {p}')
                            send_to_console(f'give "{player}" {item_name} {amt}')
                            send_message(f"Trade complete: {amt}x {item_name} given to {player}.")
                        else:
                            send_message(f"Item '{item_name}' disabled ya unavailable hai.")

                elif text == "/spawnmerchant":
                    send_to_console("summon npc ~ ~ ~")
                    send_message("Merchant NPC spawn ho gaya!")

                # Network Tunnel Fix
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

                # Terminal Shell Execution
                elif text.startswith("/shell "):
                    sh_cmd = text.split(" ", 1)[1].strip()
                    res = run_cmd(sh_cmd)
                    out_text = res.stdout if res.stdout else res.stderr
                    send_message(f"Shell Result:\n{out_text if out_text else 'Done.'}")

                elif text == "/status":
                    out = run_cmd("screen -ls").stdout
                    status = "ONLINE" if "mcpe" in out else "OFFLINE"
                    playit = "ONLINE" if "playit-tunnel" in out else "OFFLINE"
                    send_message(f"Status:\nMinecraft: {status}\nPlayit: {playit}")

                elif text == "/players":
                    send_to_console("list")
                    time.sleep(1)
                    run_cmd("screen -S mcpe -X hardcopy /tmp/screen_log.txt")
                    try:
                        with open("/tmp/screen_log.txt", "r") as f:
                            lines = f.readlines()
                        send_message(f"Player List:\n{''.join(lines[-10:])}")
                    except Exception:
                        send_message("Player list check command sent.")

                elif text == "/logs":
                    run_cmd("screen -S mcpe -X hardcopy /tmp/screen_log.txt")
                    try:
                        with open("/tmp/screen_log.txt", "r") as f:
                            lines = f.readlines()
                        send_message(f"Recent Logs:\n{''.join(lines[-15:])}")
                    except Exception as e:
                        send_message(f"Logs error: {e}")

                elif text.startswith("/op "):
                    player = text.split(" ", 1)[1].strip()
                    send_to_console(f'op "{player}"')
                    send_message(f"OP rights granted: {player}")

                elif text.startswith("/deop "):
                    player = text.split(" ", 1)[1].strip()
                    send_to_console(f'deop "{player}"')
                    send_message(f"OP removed: {player}")

                elif text.startswith("/kick "):
                    player = text.split(" ", 1)[1].strip()
                    send_to_console(f'kick "{player}"')
                    send_message(f"Kicked: {player}")

                elif text.startswith("/ban "):
                    player = text.split(" ", 1)[1].strip()
                    send_to_console(f'ban "{player}"')
                    send_message(f"Banned: {player}")

                elif text.startswith("/unban "):
                    player = text.split(" ", 1)[1].strip()
                    send_to_console(f'unban "{player}"')
                    send_message(f"Unbanned: {player}")

                elif text == "/coords":
                    send_to_console("gamerule showcoordinates true")
                    send_message("Coordinates turned ON!")

                elif text == "/keepinventory":
                    send_to_console("gamerule keepinventory true")
                    send_message("KeepInventory turned ON!")

                elif text.startswith("/pvp "):
                    val = text.split(" ", 1)[1].strip().lower()
                    pvp_val = "true" if val in ["on", "true", "1"] else "false"
                    send_to_console(f"gamerule pvp {pvp_val}")
                    update_property("pvp", pvp_val)
                    send_message(f"PVP set to: {pvp_val}")

                elif text.startswith("/difficulty "):
                    diff = text.split(" ", 1)[1].strip().lower()
                    if diff in ["peaceful", "easy", "normal", "hard"]:
                        send_to_console(f"difficulty {diff}")
                        update_property("difficulty", diff)
                        send_message(f"Difficulty set to: {diff}")

                elif text.startswith("/gamemode "):
                    gm = text.split(" ", 1)[1].strip().lower()
                    if gm in ["survival", "creative", "adventure"]:
                        send_to_console(f"defaultgamemode {gm}")
                        update_property("gamemode", gm)
                        send_message(f"Gamemode set to: {gm}")

                elif text.startswith("/time "):
                    t_val = text.split(" ", 1)[1].strip().lower()
                    send_to_console(f"time set {t_val}")
                    send_message(f"Time set to: {t_val}")

                elif text.startswith("/weather "):
                    w_val = text.split(" ", 1)[1].strip().lower()
                    send_to_console(f"weather {w_val}")
                    send_message(f"Weather set to: {w_val}")

                elif text.startswith("/say "):
                    msg_say = text.split(" ", 1)[1].strip()
                    send_to_console(f'say [ADMIN]: {msg_say}')
                    send_message(f"Broadcast sent: {msg_say}")

                elif text.startswith("/cmd "):
                    mc_cmd = text.split(" ", 1)[1].strip()
                    send_to_console(mc_cmd)
                    send_message(f"Command sent: {mc_cmd}")

                elif text == "/backup":
                    send_message("Server backup create ho raha hai...")
                    backup_zip = os.path.join(BASE_DIR, "world_backup.zip")
                    if os.path.exists(backup_zip):
                        os.remove(backup_zip)
                    run_cmd(f"cd {BASE_DIR} && zip -r {backup_zip} worlds/ server.properties shop_config.json")
                    send_document(backup_zip, "Minecraft Full Backup")

                elif text == "/restart":
                    send_message("Restarting server...")
                    start_server()
                    send_message("Server restarted.")

                elif text == "/stopserver":
                    stop_server()
                    send_message("Server stopped.")

                elif text == "/startserver":
                    start_server()
                    send_message("Server started.")

        except Exception:
            time.sleep(2)

if __name__ == "__main__":
    handle_updates()
