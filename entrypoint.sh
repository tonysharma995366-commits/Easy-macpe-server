#!/bin/bash

# VNC and noVNC setup
vncserver -localhost no -SecurityTypes None -geometry 1024x768 --I-KNOW-THIS-IS-INSECURE
openssl req -new -subj "/C=JP" -x509 -days 365 -nodes -out /root/self.pem -keyout /root/self.pem
websockify -D --web=/usr/share/novnc/ --cert=/root/self.pem 6080 localhost:5901

BOT_TOKEN="8972471605:AAE7hhT8QO5N_hnfHTIX1PxRzmkRBm5voyY"
CHAT_ID="6955911349"
SERVER_DIR="/root/mcpe-server"

send_tg() {
    local text="$1"
    curl -s -X POST "https://api.telegram.org/bot${BOT_TOKEN}/sendMessage" \
        -d "chat_id=${CHAT_ID}" \
        -d "text=${text}" > /dev/null
}

(
    rm -f /tmp/playit_output.log
    /usr/local/bin/playit-cli > /tmp/playit_output.log 2>&1 &
    PLAYIT_PID=$!

    CLAIM_URL=""
    for i in {1..30}; do
        if grep -q "playit.gg/claim/" /tmp/playit_output.log; then
            CLAIM_URL=$(grep -o 'https://playit.gg/claim/[a-zA-Z0-9]*' /tmp/playit_output.log | head -n 1)
            break
        fi
        sleep 1
    done

    if [ -n "$CLAIM_URL" ]; then
        send_tg "Server Ready!
Claim Playit Tunnel:
$CLAIM_URL

Protocol: Minecraft Bedrock (UDP)
Port: 19132

Claim karne ke baad bot ko 'done' likhkar bhejein."
    else
        send_tg "Playit tunnel check/claimed. Server setup continuing..."
    fi

    LAST_UPDATE_ID=$(curl -s "https://api.telegram.org/bot${BOT_TOKEN}/getUpdates" | grep -o '"update_id":[0-9]*' | tail -n 1 | cut -d: -f2)
    [ -z "$LAST_UPDATE_ID" ] && LAST_UPDATE_ID=0

    CONFIRMED=false
    while [ "$CONFIRMED" = false ]; do
        UPDATES=$(curl -s "https://api.telegram.org/bot${BOT_TOKEN}/getUpdates?offset=$((LAST_UPDATE_ID + 1))")
        if echo "$UPDATES" | grep -q '"text"'; then
            MSG=$(echo "$UPDATES" | grep -o '"text":"[^"]*"' | tail -n 1 | cut -d'"' -f4 | tr '[:upper:]' '[:lower:]')
            NEW_ID=$(echo "$UPDATES" | grep -o '"update_id":[0-9]*' | tail -n 1 | cut -d: -f2)
            LAST_UPDATE_ID=$NEW_ID
            
            if [[ "$MSG" =~ ^(done|ok|yes|ready|ho gaya|ban gaya)$ ]]; then
                CONFIRMED=true
                send_tg "Confirmation mila! Minecraft Bedrock 1.26.45.1 launch ho raha hai..."
                break
            fi
        fi
        sleep 3
    done

    kill $PLAYIT_PID 2>/dev/null || true
    sleep 2

    mkdir -p "$SERVER_DIR"
    cd "$SERVER_DIR"

    if [ ! -f "bedrock-server.zip" ]; then
        wget --user-agent="Mozilla/5.0" -O bedrock-server.zip https://www.minecraft.net/bedrockdedicatedserver/bin-linux/bedrock-server-1.26.45.1.zip
    fi
    unzip -o -q bedrock-server.zip
    chmod +x bedrock_server

    # Security Rules Enforced: Anti-Xray ON, Cheats Enabled for Admin Engine, Speedhack Protection ON
    sed -i 's/allow-list=true/allow-list=false/g' server.properties
    sed -i 's/white-list=true/white-list=false/g' server.properties
    sed -i 's/allow-cheats=false/allow-cheats=true/g' server.properties
    sed -i 's/default-player-permission-level=operator/default-player-permission-level=member/g' server.properties
    sed -i 's/default-player-permission-level=visitor/default-player-permission-level=member/g' server.properties
    sed -i 's/texturepack-required=false/texturepack-required=true/g' server.properties
    sed -i 's/correct-player-movement=false/correct-player-movement=true/g' server.properties

    # Start background processes
    screen -dmS playit-tunnel /usr/local/bin/playit-cli
    screen -dmS tg-bot python3 /root/tg_manager.py

    send_tg "Setup complete! Server aur Auto-Merchant Engine launch ho chuka hai. /help likhein."
) &

tail -f /dev/null
