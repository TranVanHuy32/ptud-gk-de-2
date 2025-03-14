#!/bin/bash
echo "Cloning repository..."
git clone https://github.com/TranVanHuy32/ptud-gk-de-2.git
cd ptud-gk-de-2
echo "Creating virtual environment..."
python3 -m venv venv
echo "Activating virtual environment..."
source venv/bin/activate
echo "Installing dependencies..."
pip install -r requirements.txt
echo "Running application..."
app run