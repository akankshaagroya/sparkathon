# Mumbai Cold Chain Rescue System

## 🚀 Overview
A robust, scalable, and AI-driven cold chain rescue and monitoring system for Mumbai, designed for real-world logistics and emergency response. The system features live truck monitoring, instant rescue dispatch, and advanced multi-truck rescue (load splitting) for scenarios where a single truck cannot handle a rescue. Built for demo, pitch, and real deployment.

---

## 🌟 Key Features

### 1. **Live Rescue Operations Dashboard**
- Real-time map of Mumbai with all trucks, failed trucks, and rescue operations visualized.
- Distinct icons for failed trucks (🆘) and rescue trucks (🚚/🚑) for instant clarity.
- Animated rescue routes and live progress/ETA tracking.
- Sidebar with active rescue details, truck stats, and live rescue logs.

### 2. **AI-Optimized Rescue Dispatch**
- Automatic detection of truck failures (temperature, battery, reliability, etc.).
- AI selects the optimal rescue truck(s) based on distance, battery, capacity, and reliability.
- **Multi-truck rescue (load splitting):**
  - If a single truck cannot handle a rescue, the system dispatches multiple real trucks in parallel, splitting the load.
  - All rescue trucks are always real, named vehicles (never placeholders or "undefined").
  - Demo scenario: The second manual failure always triggers a real, parallel multi-truck rescue for demonstration.
- All rescue trucks and routes are shown on the map and in the sidebar, with real names and stats.

### 3. **Frontend & Visualization**
- Modern, responsive UI with clear status banners and controls.
- Rescue trucks and routes are color-coded for clarity.
- Rescue info panel always shows real truck names, stats, and load share for each rescuer.
- No placeholder or undefined names ever shown.
- All money/spoilage/cost metrics and logs are removed from the UI.
- Rescue logs show only relevant operational info (no backend errors or cost/spoilage data).

### 4. **Backend & API**
- `/truck_status` and `/rescue_routes` endpoints provide live truck and rescue data.
- `/system_logs` endpoint returns all rescue logs (no cost/spoilage info).
- Multi-truck rescue logic in backend ensures all rescuers are real, available trucks, and each has a top-level `rescue_truck_id`.
- All backend errors are logged but never shown to the user (UI always stays clean).
- No money/spoilage metrics in any logs or API responses.

### 5. **Special Features**
- **Multi-truck rescue with load splitting** (real trucks only, never placeholders).
- **Visual clarity:**
  - Rescue truck icons (🚚/🚑) and failed truck icons (🆘) on the map.
  - Animated, color-coded rescue routes.
- **Robustness:**
  - No undefined/placeholder names in any rescue scenario.
  - All errors are suppressed from the UI.
- **Demo/Pitch Ready:**
  - Forced multi-truck rescue scenario for demo (second manual failure).
  - Clean, modern UI for live presentations.

---

## 🚦 Manual Failure Triggers UI

Below is a screenshot of the Manual Failure Triggers panel, which allows you to simulate various truck failure scenarios for demo and testing purposes:

![Manual Failure Triggers](docs/manual_failure_triggers.png)

- **Temperature Critical:** Cold chain breach > 10°C
- **Battery Drain:** Power critical < 5%
- **Engine Failure:** Mechanical breakdown
- **GPS Signal Lost:** Communication error
- **Refrigeration Unit:** Cooling system failure
- **Route Blocked:** Traffic obstruction

---

## 🛠️ How to Run

1. **Install dependencies:**
   ```bash
   pip install -r requirements.txt
   ```
2. **Start the backend:**
   ```bash
   cd rescue_manager
   python enhanced_main.py
   ```
3. **Open the frontend:**
   - Open `rescue_manager/rescue_ops.html` in your browser.

---

## 📋 Project Structure
- `rescue_manager/` — Backend, rescue logic, and frontend UI (HTML/JS)
- `dataset/` — Dataset generation and simulation scripts
- `maptry/` — Map generation and visualization utilities

---

## 🏆 Demo Tips
- Trigger a manual failure to see a single-truck rescue.
- Trigger a second manual failure to see a real, parallel multi-truck rescue (load splitting) in action.
- Watch the map and sidebar update with real truck names, stats, and animated rescue routes.

---

## 👥 Authors & Credits
- Developed for Sparkathon 2025

---

## 📄 License
[MIT License]