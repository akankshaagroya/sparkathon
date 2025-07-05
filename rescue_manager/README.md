# 🚛 Mumbai Cold Chain Rescue Demo

A **production-ready, minimal UI** for real-time cold chain truck monitoring, manual failure triggering, and automated rescue operations.

---

## 🚀 Quick Start (Manual)

1. **Install dependencies**  
   ```bash
   pip install -r requirements.txt
   ```

2. **Start the backend server**  
   ```bash
   python enhanced_main.py
   ```

3. **Open your browser and access:**  
   - **Homepage:** [http://localhost:8000](http://localhost:8000)  
   - **Normal Operations Map:** [http://localhost:8000/normal_ops](http://localhost:8000/normal_ops)  
   - **Rescue Operations Map:** [http://localhost:8000/rescue_ops](http://localhost:8000/rescue_ops)  
   - **API Docs:** [http://localhost:8000/docs](http://localhost:8000/docs)

---

## 🛠️ What This Demo Solves

- **Manual Failure Triggers:**  
  Trigger realistic breakdowns (temperature, battery, engine, GPS, refrigeration, route block) for any truck, via the homepage.

- **Automatic Rescue Dispatch & Completion:**  
  When a truck fails, the system auto-selects the best available rescue truck using a 6-factor scoring algorithm and dispatches it. Rescue completion is simulated and visualized.

- **Live Map Visualization:**  
  - **Normal Ops:** Shows all trucks, each with a visually distinct route color, delivery count, and status.
  - **Rescue Ops:** Shows failed truck, rescue truck, animated rescue route, and detailed rescue analytics.

- **Unified Scenario:**  
  All maps and UI reflect the same live backend state.

- **Distinct Route Colors:**  
  Each truck always gets a unique, ultra-distinct color from a fixed palette, regardless of truck ID.

- **Realistic Failure Types:**  
  Simulate temperature, battery, engine, GPS, refrigeration, and route block failures.

- **Visual Clarity:**  
  See which vehicle is coming to rescue, route progress, and automatic disappearance of rescue visuals when complete.

---

## 🧩 Main Functions/Flows

- **/truck_status**: Get live status of all trucks (location, temp, battery, status, route, etc.)
- **/trigger_failure/{type}**: Manually trigger a specific failure type for a random operational truck.
- **/rescue_routes**: Get all active rescue operations and routes.
- **/system_logs**: Get the latest system logs.
- **/normal_ops**: Map UI for normal operations (distinct routes, delivery counts, status).
- **/rescue_ops**: Map UI for rescue operations (failed/rescue trucks, animated rescue route, analytics).
- **/start_simulation**: (Optional) Start background simulation for rescue completion.
- **/stop_simulation**: (Optional) Stop background simulation.

---

**No .bat files, no scripts needed—just run the Python backend and open the browser!**

If you need a more detailed or customized README, let me know!
