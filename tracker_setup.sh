#!/bin/bash
# ============================================================
# SneakerDrop FR — Click Tracker Setup (VPS Hetzner)
# Lance le serveur FastAPI sur le port 8421
# ============================================================
set -e

TRACKER_DIR="/opt/sneakerdropfr"
SERVICE_NAME="sneaker-tracker"
PORT=8421
DB_PATH="/var/data/clicks.db"
VENV="$TRACKER_DIR/venv"

echo "=== SneakerDrop FR Click Tracker Setup ==="

# 1. Créer les répertoires
mkdir -p /var/data "$TRACKER_DIR"

# 2. Copier click_tracker.py
cp "$(dirname "$0")/click_tracker.py" "$TRACKER_DIR/click_tracker.py"

# 3. Venv + dépendances
if [ ! -d "$VENV" ]; then
    echo "→ Création du venv Python..."
    python3 -m venv "$VENV"
fi
"$VENV/bin/pip" install --quiet --upgrade pip
"$VENV/bin/pip" install --quiet fastapi uvicorn

# 4. Générer un token admin aléatoire si pas déjà défini
TOKEN_FILE="/var/data/tracker_admin_token"
if [ ! -f "$TOKEN_FILE" ]; then
    python3 -c "import secrets; print(secrets.token_urlsafe(24))" > "$TOKEN_FILE"
    echo "→ Token admin généré : $(cat $TOKEN_FILE)"
    echo "   Accès admin : http://TON_IP:$PORT/admin?token=$(cat $TOKEN_FILE)"
else
    echo "→ Token admin existant : $(cat $TOKEN_FILE)"
fi
ADMIN_TOKEN=$(cat "$TOKEN_FILE")

# 5. Créer le service systemd
cat > "/etc/systemd/system/$SERVICE_NAME.service" << SYSTEMD
[Unit]
Description=SneakerDrop FR Click Tracker
After=network.target

[Service]
Type=simple
User=root
WorkingDirectory=$TRACKER_DIR
Environment="TRACKER_PORT=$PORT"
Environment="TRACKER_DB=$DB_PATH"
Environment="SITE_ORIGIN=https://sneakerdropfr.fr"
Environment="ADMIN_TOKEN=$ADMIN_TOKEN"
ExecStart=$VENV/bin/python click_tracker.py
Restart=always
RestartSec=5
StandardOutput=journal
StandardError=journal

[Install]
WantedBy=multi-user.target
SYSTEMD

# 6. Activer et démarrer
systemctl daemon-reload
systemctl enable "$SERVICE_NAME"
systemctl restart "$SERVICE_NAME"

echo ""
echo "=== Tracker démarré ==="
echo "  Status   : systemctl status $SERVICE_NAME"
echo "  Logs     : journalctl -u $SERVICE_NAME -f"
echo "  Health   : curl http://localhost:$PORT/health"
echo "  Admin    : http://TON_IP:$PORT/admin?token=$ADMIN_TOKEN"
echo "  Stats    : curl http://localhost:$PORT/stats?token=$ADMIN_TOKEN"
echo ""
echo "⚠  Pense à ouvrir le port $PORT dans le pare-feu Hetzner :"
echo "   ufw allow $PORT/tcp"
