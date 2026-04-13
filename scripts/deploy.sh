#!/bin/bash
# Run this script on the Oracle Cloud VM after SSH-ing in.
# Usage: bash deploy.sh

set -e

echo "=== FinTwit Monitor - Oracle Cloud Setup ==="

# Install Python and pip
echo "[1/5] Installing Python..."
sudo apt-get update -qq
sudo apt-get install -y -qq python3 python3-pip python3-venv git cron

# Clone the repo (or copy files)
echo "[2/5] Setting up project..."
mkdir -p ~/fintwit
cd ~/fintwit

# Create virtual environment
python3 -m venv venv
source venv/bin/activate

# Copy requirements and install
pip install --quiet twikit httpx

echo "[3/5] Setting up environment variables..."
if [ ! -f .env ]; then
    cat > .env << 'ENVEOF'
TWITTER_AUTH_TOKEN=REPLACE_ME
TWITTER_CT0=REPLACE_ME
GMAIL_USER=shreychande@gmail.com
GMAIL_APP_PASSWORD=REPLACE_ME
NTFY_TOPIC=REPLACE_ME
ENVEOF
    echo ">>> IMPORTANT: Edit ~/fintwit/.env with your actual credentials!"
    echo ">>>   nano ~/fintwit/.env"
fi

echo "[4/5] Setting up cron jobs..."
# Check tweets every 15 minutes
CRON_CHECK="*/15 * * * * cd $HOME/fintwit && source venv/bin/activate && source .env && python3 -m src all >> /tmp/fintwit.log 2>&1"
# Remove old fintwit cron entries, then add new ones
(crontab -l 2>/dev/null | grep -v 'fintwit' ; echo "$CRON_CHECK") | crontab -

echo "[5/5] Starting cron service..."
sudo systemctl enable cron
sudo systemctl start cron

echo ""
echo "=== Setup complete! ==="
echo ""
echo "Next steps:"
echo "  1. Edit credentials:  nano ~/fintwit/.env"
echo "  2. Test manually:     cd ~/fintwit && source venv/bin/activate && source .env && python3 -m src check"
echo "  3. View logs:         tail -f /tmp/fintwit.log"
echo ""
echo "The monitor will run every 15 minutes automatically."
