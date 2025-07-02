@echo off
echo 🚚 Truck Route Optimizer - Quick Start
echo =====================================

echo.
echo 1. Installing dependencies...
pip install -r requirements.txt

echo.
echo 2. Generating sample data...
python main.py generate-sample

echo.
echo 3. Running optimization...
python main.py optimize

echo.
echo ✅ Quick start complete!
echo 📁 Check the 'output' folder for results
echo 🗺️ Open 'output/route_map.html' to see the interactive map

pause
