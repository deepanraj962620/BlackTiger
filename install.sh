#!/usr/bin/env bash
set -e
echo -e "\033[1;32mBlackTiger v4 Installer - Deepanraj C\033[0m"
sudo apt update
sudo apt install -y python3 python3-pip python3-venv
python3 -m venv .venv
source .venv/bin/activate
python3 -m pip install --upgrade pip
pip install -r requirements.txt
chmod +x run.sh
echo "Install complete. Run ./run.sh"
