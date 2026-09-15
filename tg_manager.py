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
BEHAVIOR_PACK_DIR = os.path.join(BASE_DIR, "behavior_packs", "auto_shop")

# Pre-configured default items: Food, seeds, building ON; Rare items OFF
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
    build_and_inject_behavior_pack()
    cmd = f'screen -dmS mcpe bash -c "cd {BASE_DIR} && LD_LIBRARY_PATH=. ./bedrock_server"'
    run_cmd(cmd)
    time.sleep(2)

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
    # Shop update hote hi Behavior Pack update ho jayega
    build_and_inject_behavior_pack()

def get_active_world():
    if not os.path.exists(PROPERTIES_FILE):
        return "Bedrock level"
    with open(PROPERTIES_FILE, "r") as f:
        for line in f:
            if line.startswith("level-name="):
                return line.split("=", 1)[1].strip()
    return "Bedrock level"

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

# Automatic Behavior Pack Engine jo Trades.json khud banata hai
def build_and_inject_behavior_pack():
    cfg = load_shop_config()
    trades_list = []
    
    for category, items in cfg.items():
        for item_name, data in items.items():
            if data.get("enabled", False):
                curr = data.get("currency", "emerald")
                price = data.get("price", 1)
                count = data.get("count", 1)
                
                curr_item = f"minecraft:{curr}" if not curr.startswith("minecraft:") else curr
                trade_item = f"minecraft:{item_name}" if not item_name.startswith("minecraft:") else item_name
                
                # Agar price 64 se zyada hai (jaise 128 diamonds / 2 stacks)
                wants = []
                if price > 64:
                    wants.append({"item": curr_item, "quantity": 64})
                    wants.append({"item": curr_item, "quantity": min(64, price - 64)})
                else:
                    wants.append({"item": curr_item, "quantity": price})
                    
                trades_list.append({
                    "wants": wants,
                    "gives": [{"item": trade_item, "quantity": count}],
                    "max_uses": 999999
                })

    os.makedirs(os.path.join(BEHAVIOR_PACK_DIR, "trading"), exist_ok=True)
    os.makedirs(os.path.join(BEHAVIOR_PACK_DIR, "entities"), exist_ok=True)
    
    # 1. Manifest
    manifest_data = {
        "format_version": 2,
        "header": {
            "name": "Server Auto Shop Pack",
            "description": "Auto generated trades for server merchant",
            "uuid": "2c678a10-7212-429a-a82a-43187b41e991",
            "version": [1, 0, 0],
            "min_engine_version": [1, 20, 0]
        },
        "modules": [
            {
                "type": "data",
                "uuid": "8f3192aa-812a-40a1-a123-8837194ab512",
                "version": [1, 0, 0]
            }
        ]
    }
    with open(os.path.join(BEHAVIOR_PACK_DIR, "manifest.json"), "w") as f:
        json.dump(manifest_data, f, indent=2)
        
    # 2. Trades JSON
    trades_data = {"tiers": [{"trades": trades_list}]}
    with open(os.path.join(BEHAVIOR_PACK_DIR, "trading", "economy_trades.json"), "w") as f:
        json.dump(trades_data, f, indent=2)
        
    # 3. Entity definition override for Wandering Trader
    entity_data = {
        "format_version": "1.16.0",
        "minecraft:entity": {
            "description": {
                "identifier": "minecraft:wandering_trader",
                "is_spawnable": True,
                "is_summonable": True,
                "is_experimental": False
            },
            "component_groups": {},
            "components": {
                "minecraft:type_family": {"family": ["wandering_trader", "mob"]},
                "minecraft:breathable": {"total_supply": 15, "suffocate_when_rescuing": False},
                "minecraft:nameable": {},
                "minecraft:health": {"value": 20, "max": 20},
                "minecraft:economy_trade_table": {
                    "display_name": "Server Merchant",
                    "table": "trading/economy_trades.json",
                    "new_screen": True
                },
                "minecraft:physics": {},
                "minecraft:pushable": {"is_pushable": False}
            }
        }
    }
    with open(os.path.join(BEHAVIOR_PACK_DIR, "entities", "wandering_trader.json"), "w") as f:
        json.dump(entity_data, f, indent=2)

    # 4. Link into active world
    world_name = get_active_world()
    world_path = os.path.join(WORLDS_DIR, world_name)
    os.makedirs(world_path, exist_ok=True)
    world_pack_file = os.path.join(world_path, "world_behavior_packs.json")
    
    pack_entry = [{"pack_id": "2c678a10-7212-429a-a82a-43187b41e991", "version": [1, 0, 0]}]
    with open(world_pack_file, "w") as f:
        json.dump(pack_entry, f, indent=2)

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

HELP_TEXT = """Minecraft Auto-Shop & Server Control Panel

Custom Merchant:
/spawnmerchant <player> - Pre-programmed Merchant spawn karein
/shop - Active items & price list
/shopset <item> <on|off> - Item allow ya block karein
/customprice <item> <currency> <amount> <count>
   Example: /customprice elytra diamond 128 1

World & Generation:
/seed <number> - New world with seed
/backup - Full backup zip
[Send .zip/.mcworld] - Upload custom world

Security & Rules:
/propertyprotection <on|off> - Anti-Griefing toggle
/chestlock <on|off> - Chest protection toggle
/antixray <on|off> - Force server texturepack
/coords - Coordinates ON
/keepinventory - KeepInventory ON

Player Admin:
/op <player> / /deop <player>
/kick <player> / /ban <player> / /unban <player>
/fixtunnel - Restart Playit
/restart / /status / /logs
/cmd <cmd> / /shell <cmd>
"""

def handle_updates():
    offset = 0
    start_server()
    send_message("Minecraft Server & Pre-Programmed Shop Online!\nType /help sabhi commands ke liye.")
    
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

                # Pre-programmed Merchant Spawn
                elif text.startswith("/spawnmerchant"):
                    parts = text.split(maxsplit=1)
                    target = parts[1].strip() if len(parts) > 1 else "@p"
                    
                    send_to_console(f'execute at {target} run summon wandering_trader ~ ~ ~ minecraft:entity_born "Server Merchant"')
                    time.sleep(1)
                    send_to_console('effect @e[name="Server Merchant"] slowness 999999 255 true')
                    send_to_console('effect @e[name="Server Merchant"] resistance 999999 255 true')
                    send_message(f"Pre-Programmed Merchant '{target}' ke paas spawn ho gaya!\nAb uspar seedha tap karein, custom trades ka menu khul jayega.")

                # Shop Price & Stock Control
                elif text == "/shop":
                    cfg = load_shop_config()
                    out = "Active Merchant Trades:\n\n"
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
                            send_message(f"'{item_name}' set to: {'ENABLED' if state else 'DISABLED'}. Trades updated!")
                        else:
                            send_message(f"Item '{item_name}' shop catalog me nahi mila.")

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
                        send_message(f"Custom Price Set: {count}x {item_name} = {price} {curr}!\nTrades automatically update ho gaye.")

                # World Seed Generation
                elif text.startswith("/seed"):
                    parts = text.split(maxsplit=1)
                    if len(parts) < 2:
                        send_message("Seed number likhein! Example: /seed 987654321")
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
                        send_message("Property Protection ENABLED! Players blocks nahi tod payenge.")
                    else:
                        send_to_console("gamerule immutableworld false")
                        send_message("Property Protection DISABLED!")

                # Chest Protection
                elif text.startswith("/chestlock "):
                    mode = text.split(" ", 1)[1].strip().lower()
                    if mode in ["on", "enable", "true"]:
                        send_to_console("scoreboard objectives add chestprotect dummy")
                        send_message("Chest Protection ENABLED!")
                    else:
                        send_message("Chest Protection DISABLED!")

                # Anti-Xray Texture Requirement
                elif text.startswith("/antixray "):
                    mode = text.split(" ", 1)[1].strip().lower()
                    val = "true" if mode in ["on", "enable", "true"] else "false"
                    update_property("texturepack-required", val)
                    send_message(f"Anti-Xray force requirement set to: {val}.")

                # Network Tunnel Fix
                elif text == "/fixtunnel":
                    send_message("Playit restart ho raha hai...")
                    run_cmd("pkill -9 playit-cli")
                    run_cmd("screen -S playit-tunnel -X quit")
                    time.sleep(1)
                    run_cmd("screen -dmS playit-tunnel /usr/local/bin/playit-cli")
                    send_message("Playit Tunnel restart ho chuka hai!")

                # Admin Controls
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

                elif text == "/status":
                    out = run_cmd("screen -ls").stdout
                    status = "ONLINE" if "mcpe" in out else "OFFLINE"
                    playit = "ONLINE" if "playit-tunnel" in out else "OFFLINE"
                    send_message(f"Status:\nMinecraft: {status}\nPlayit: {playit}")

                elif text == "/backup":
                    send_message("Full backup banaya ja raha hai...")
                    backup_zip = os.path.join(BASE_DIR, "world_backup.zip")
                    if os.path.exists(backup_zip):
                        os.remove(backup_zip)
                    run_cmd(f"cd {BASE_DIR} && zip -r {backup_zip} worlds/ server.properties shop_config.json behavior_packs/")
                    send_document(backup_zip, "Minecraft Server Backup")

                elif text.startswith("/shell "):
                    res = run_cmd(text.split(" ", 1)[1].strip())
                    send_message(f"Output:\n{res.stdout or res.stderr or 'Done'}")

                elif text.startswith("/cmd "):
                    send_to_console(text.split(" ", 1)[1].strip())
                    send_message("Command executed!")

                elif text == "/restart":
                    send_message("Server restart ho raha hai...")
                    start_server()
                    send_message("Server restarted.")

        except Exception:
            time.sleep(2)

if __name__ == "__main__":
    handle_updates()
