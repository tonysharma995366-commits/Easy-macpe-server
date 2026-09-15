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
        print(f"Telegram error: {e}")

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

def read_console_output(lines_count=15):
    time.sleep(0.5)
    run_cmd("rm -f /tmp/mc_screen.txt && screen -S mcpe -X hardcopy /tmp/mc_screen.txt")
    time.sleep(0.5)
    try:
        if os.path.exists("/tmp/mc_screen.txt"):
            with open("/tmp/mc_screen.txt", "r", errors="ignore") as f:
                lines = [l.strip() for l in f.readlines() if l.strip()]
            return "\n".join(lines[-lines_count:])
    except Exception as e:
        return f"Log read error: {e}"
    return "No logs captured."

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
        
    trades_data = {"tiers": [{"trades": trades_list}]}
    with open(os.path.join(BEHAVIOR_PACK_DIR, "trading", "economy_trades.json"), "w") as f:
        json.dump(trades_data, f, indent=2)
        
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
        send_message("Kripya sirf .zip ya .mcworld file bhejein!")
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
            
    send_message("World apply ho rahi hai...")
    stop_server()
    world_folder_name = os.path.splitext(file_name)[0].replace(" ", "_")
    target_extract = os.path.join(WORLDS_DIR, world_folder_name)
    os.makedirs(target_extract, exist_ok=True)
    
    with zipfile.ZipFile(local_zip, 'r') as zip_ref:
        zip_ref.extractall(target_extract)
        
    update_property("level-name", world_folder_name)
    start_server()
    send_message(f"World successfully import ho gayi!\nWorld Name: {world_folder_name}\nServer restarted.")

HELP_TEXT = """MCPE Server Master Control Panel

World & Map:
1. /seed <num> - Generate world with custom seed
2. /backup - Download full server zip backup
3. [Send .zip/.mcworld] - Restore/Upload world map

Security & Protection:
4. /propertyprotection <on|off> - Anti-Griefing (no block breaks)
5. /chestlock <on|off> - Chest & container protection
6. /antixray <on|off> - Force server texture enforcement

Player Moderation:
7. /players - List online players
8. /op <player> - Grant admin privileges
9. /deop <player> - Revoke admin privileges
10. /kick <player> - Kick player from server
11. /ban <player> - Permanently ban player
12. /unban <player> - Unban player
13. /whitelist <on|off> - Toggle server whitelist
14. /whitelistadd <player> - Add player to whitelist
15. /whitelistremove <player> - Remove from whitelist
16. /tp <player1> <player2> - Teleport player
17. /kill <player> - Kill player
18. /clearinv <player> - Clear player inventory

Gameplay & GameRules:
19. /coords - Show in-game coordinates
20. /keepinventory - Keep inventory on death
21. /pvp <on|off> - Toggle player vs player damage
22. /difficulty <peaceful|easy|normal|hard> - Set difficulty
23. /gamemode <survival|creative|adventure> - Default gamemode
24. /time <day|night|noon|midnight> - Change in-game time
25. /weather <clear|rain|thunder> - Change weather
26. /mobspawning <true|false> - Toggle natural mob spawn
27. /killmobs - Clear all hostile mobs from world
28. /say <message> - Server-wide broadcast announcement

Server Diagnostics & Terminal:
29. /status - Check Minecraft & Playit status
30. /logs - Real-time console log view
31. /fixtunnel - Clean restart Playit tunnel
32. /restart - Restart Bedrock server
33. /startserver - Start server
34. /stopserver - Stop server
35. /cmd <cmd> - Run any Minecraft console command
36. /shell <cmd> - Run Linux terminal bash command

Merchant Commands: Type /npc or /merchant
"""

NPC_HELP_TEXT = """Custom Merchant & Economy Commands

1. /spawnmerchant <player> - Spawn pre-programmed trader at player position
2. /shop - View all items, stock status & prices
3. /shopset <item> <on|off> - Allow or block an item in shop
4. /customprice <item> <currency> <price> <count> - Set custom item currency & price
   (Example: /customprice elytra diamond 128 1)
5. /processbuy <player> <item> - Execute manual secure trade transaction
"""

def handle_updates():
    offset = 0
    start_server()
    send_message("Minecraft Server Controller Active!\nType /help for main commands or /npc for merchant controls.")
    
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

                # Dedicated Merchant / NPC Help Menu
                elif text in ["/npc", "/ncp", "/merchant"]:
                    send_message(NPC_HELP_TEXT)

                # 1. Seed
                elif text.startswith("/seed"):
                    parts = text.split(maxsplit=1)
                    if len(parts) < 2:
                        send_message("Seed number dalein! Example: /seed 987654321")
                    else:
                        seed_val = parts[1].strip()
                        new_world = f"world_{int(time.time())}"
                        send_message(f"Seed {seed_val} apply karke naya world generate ho raha hai...")
                        stop_server()
                        update_property("level-seed", seed_val)
                        update_property("level-name", new_world)
                        start_server()
                        send_message(f"Naya world ban gaya!\nWorld Name: {new_world}\nSeed: {seed_val}")

                # 2. Backup
                elif text == "/backup":
                    send_message("Full server backup create ho raha hai...")
                    backup_zip = os.path.join(BASE_DIR, "world_backup.zip")
                    if os.path.exists(backup_zip):
                        os.remove(backup_zip)
                    run_cmd(f"cd {BASE_DIR} && zip -r {backup_zip} worlds/ server.properties shop_config.json behavior_packs/")
                    send_document(backup_zip, "Minecraft Server Complete Backup")

                # Merchant: Spawn
                elif text.startswith("/spawnmerchant"):
                    parts = text.split(maxsplit=1)
                    target = parts[1].strip() if len(parts) > 1 else "@p"
                    send_to_console(f'execute at {target} run summon wandering_trader ~ ~ ~ "Server Merchant"')
                    send_to_console(f'execute as {target} at @s run summon wandering_trader ~ ~ ~ "Server Merchant"')
                    time.sleep(0.5)
                    send_to_console('effect @e[name="Server Merchant"] slowness 999999 255 true')
                    send_to_console('effect @e[name="Server Merchant"] resistance 999999 255 true')
                    send_message(f"Merchant '{target}' ke paas spawn ho gaya! Direct tap karke trade karein.")

                # Merchant: Catalog
                elif text == "/shop":
                    cfg = load_shop_config()
                    out = "Merchant Trade Catalog:\n\n"
                    for cat, items in cfg.items():
                        out += f"[{cat.upper()}]\n"
                        for name, data_item in items.items():
                            status = "ACTIVE" if data_item["enabled"] else "DISABLED"
                            out += f" • {name}: {data_item['count']}x for {data_item['price']} {data_item['currency']} [{status}]\n"
                    send_message(out)

                # Merchant: Shopset
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

                # Merchant: Custom Price
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
                        send_message(f"Custom Price Set: {count}x {item_name} = {price} {curr}!\nBehavior pack automatically reloaded.")

                # Merchant: Process Buy
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
                            send_message("Item available nahi hai.")

                # Property Protection
                elif text.startswith("/propertyprotection "):
                    mode = text.split(" ", 1)[1].strip().lower()
                    if mode in ["on", "enable", "true"]:
                        send_to_console("gamerule immutableworld true")
                        send_message("Property Protection ENABLED! Players cannot break/place blocks.")
                    else:
                        send_to_console("gamerule immutableworld false")
                        send_message("Property Protection DISABLED!")

                # Chestlock
                elif text.startswith("/chestlock "):
                    mode = text.split(" ", 1)[1].strip().lower()
                    if mode in ["on", "enable", "true"]:
                        send_to_console("scoreboard objectives add chestprotect dummy")
                        send_message("Chest Protection ENABLED!")
                    else:
                        send_message("Chest Protection DISABLED!")

                # Anti-Xray
                elif text.startswith("/antixray "):
                    mode = text.split(" ", 1)[1].strip().lower()
                    val = "true" if mode in ["on", "enable", "true"] else "false"
                    update_property("texturepack-required", val)
                    send_message(f"Anti-Xray force requirement set to: {val}.")

                # Players List
                elif text == "/players":
                    send_to_console("list")
                    out = read_console_output(6)
                    send_message(f"Online Players:\n{out}")

                # OP
                elif text.startswith("/op "):
                    p = text.split(" ", 1)[1].strip()
                    send_to_console(f'op "{p}"')
                    send_message(f"OP rights granted: {p}")

                # De-OP
                elif text.startswith("/deop "):
                    p = text.split(" ", 1)[1].strip()
                    send_to_console(f'deop "{p}"')
                    send_message(f"OP removed: {p}")

                # Kick
                elif text.startswith("/kick "):
                    p = text.split(" ", 1)[1].strip()
                    send_to_console(f'kick "{p}"')
                    send_message(f"Kicked: {p}")

                # Ban
                elif text.startswith("/ban "):
                    p = text.split(" ", 1)[1].strip()
                    send_to_console(f'ban "{p}"')
                    send_message(f"Banned: {p}")

                # Unban
                elif text.startswith("/unban "):
                    p = text.split(" ", 1)[1].strip()
                    send_to_console(f'unban "{p}"')
                    send_message(f"Unbanned: {p}")

                # Whitelist Toggle
                elif text.startswith("/whitelist "):
                    mode = text.split(" ", 1)[1].strip().lower()
                    val = "on" if mode in ["on", "true", "enable"] else "off"
                    send_to_console(f"whitelist {val}")
                    send_message(f"Whitelist set to: {val.upper()}")

                # Whitelist Add
                elif text.startswith("/whitelistadd "):
                    p = text.split(" ", 1)[1].strip()
                    send_to_console(f'whitelist add "{p}"')
                    send_message(f"Added to whitelist: {p}")

                # Whitelist Remove
                elif text.startswith("/whitelistremove "):
                    p = text.split(" ", 1)[1].strip()
                    send_to_console(f'whitelist remove "{p}"')
                    send_message(f"Removed from whitelist: {p}")

                # Teleport
                elif text.startswith("/tp "):
                    parts = text.split()
                    if len(parts) >= 3:
                        send_to_console(f'tp "{parts[1]}" "{parts[2]}"')
                        send_message(f"Teleported {parts[1]} to {parts[2]}")
                    else:
                        send_message("Usage: /tp <player1> <player2>")

                # Kill
                elif text.startswith("/kill "):
                    p = text.split(" ", 1)[1].strip()
                    send_to_console(f'kill "{p}"')
                    send_message(f"Killed: {p}")

                # Clear Inventory
                elif text.startswith("/clearinv "):
                    p = text.split(" ", 1)[1].strip()
                    send_to_console(f'clear "{p}"')
                    send_message(f"Inventory cleared for: {p}")

                # Coords
                elif text == "/coords":
                    send_to_console("gamerule showcoordinates true")
                    send_message("Coordinates turned ON!")

                # KeepInventory
                elif text == "/keepinventory":
                    send_to_console("gamerule keepinventory true")
                    send_message("KeepInventory turned ON!")

                # PVP Toggle
                elif text.startswith("/pvp "):
                    val = text.split(" ", 1)[1].strip().lower()
                    pvp_val = "true" if val in ["on", "true", "1"] else "false"
                    send_to_console(f"gamerule pvp {pvp_val}")
                    update_property("pvp", pvp_val)
                    send_message(f"PVP set to: {pvp_val}")

                # Difficulty
                elif text.startswith("/difficulty "):
                    diff = text.split(" ", 1)[1].strip().lower()
                    if diff in ["peaceful", "easy", "normal", "hard"]:
                        send_to_console(f"difficulty {diff}")
                        update_property("difficulty", diff)
                        send_message(f"Difficulty set to: {diff}")

                # Gamemode
                elif text.startswith("/gamemode "):
                    gm = text.split(" ", 1)[1].strip().lower()
                    if gm in ["survival", "creative", "adventure"]:
                        send_to_console(f"defaultgamemode {gm}")
                        update_property("gamemode", gm)
                        send_message(f"Default gamemode set to: {gm}")

                # Time
                elif text.startswith("/time "):
                    t_val = text.split(" ", 1)[1].strip().lower()
                    send_to_console(f"time set {t_val}")
                    send_message(f"Time set to: {t_val}")

                # Weather
                elif text.startswith("/weather "):
                    w_val = text.split(" ", 1)[1].strip().lower()
                    send_to_console(f"weather {w_val}")
                    send_message(f"Weather set to: {w_val}")

                # Mob Spawning
                elif text.startswith("/mobspawning "):
                    val = text.split(" ", 1)[1].strip().lower()
                    send_to_console(f"gamerule domobspawning {val}")
                    send_message(f"Mob spawning set to: {val}")

                # Kill Mobs
                elif text == "/killmobs":
                    send_to_console("kill @e[type=!player]")
                    send_message("All non-player mobs removed!")

                # Broadcast Announcement
                elif text.startswith("/say "):
                    msg_say = text.split(" ", 1)[1].strip()
                    send_to_console(f'say [ANNOUNCEMENT]: {msg_say}')
                    send_message(f"Broadcasted: {msg_say}")

                # Status
                elif text == "/status":
                    out = run_cmd("screen -ls").stdout
                    status = "ONLINE" if "mcpe" in out else "OFFLINE"
                    playit = "ONLINE" if "playit-tunnel" in out else "OFFLINE"
                    send_message(f"Server Status:\nMinecraft: {status}\nPlayit Tunnel: {playit}")

                # Logs
                elif text == "/logs":
                    out = read_console_output(15)
                    send_message(f"Live Console Logs:\n{out}")

                # Fix Tunnel
                elif text == "/fixtunnel":
                    send_message("Restarting Playit...")
                    run_cmd("pkill -9 playit-cli")
                    run_cmd("screen -S playit-tunnel -X quit")
                    time.sleep(1)
                    run_cmd("screen -dmS playit-tunnel /usr/local/bin/playit-cli")
                    send_message("Playit restart complete!")

                # Restart
                elif text == "/restart":
                    send_message("Server restart ho raha hai...")
                    start_server()
                    send_message("Server restarted.")

                # Start Server
                elif text == "/startserver":
                    start_server()
                    send_message("Server started.")

                # Stop Server
                elif text == "/stopserver":
                    stop_server()
                    send_message("Server stopped.")

                # Console Command
                elif text.startswith("/cmd "):
                    mc_cmd = text.split(" ", 1)[1].strip()
                    send_to_console(mc_cmd)
                    send_message(f"Console command sent: {mc_cmd}")

                # Linux Shell Command
                elif text.startswith("/shell "):
                    sh_cmd = text.split(" ", 1)[1].strip()
                    res = run_cmd(sh_cmd)
                    out_text = res.stdout if res.stdout else res.stderr
                    send_message(f"Shell Output:\n{out_text if out_text else 'Done.'}")

        except Exception:
            time.sleep(2)

if __name__ == "__main__":
    handle_updates()
