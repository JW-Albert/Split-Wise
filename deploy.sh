#!/bin/bash

echo "Updating and upgrading system"
sudo apt update && sudo apt upgrade -y

echo "Installing Python and pip"
sudo apt install python3 python3-pip python3-venv -y

echo "Creating virtual environment"
python3 -m venv venv

echo "Activating virtual environment"
source venv/bin/activate

echo "Installing dependencies"
pip install --upgrade pip
pip install -r requirements.txt

echo "Deploy complete"