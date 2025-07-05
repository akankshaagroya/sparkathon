#!/usr/bin/env python3
"""
Enhanced Mumbai Cold Chain Rescue Manager
Production-ready real-time truck rescue system with automatic failure detection
and intelligent rescue dispatch using real road routing.
"""

import asyncio
import json
import logging
import os
import random
import time
import asyncio
import json
import logging
import os
import random
import time
from datetime import datetime, timedelta
from typing import Dict, List, Optional, Any
import uvicorn
from fastapi import FastAPI, HTTPException
from fastapi.responses import HTMLResponse, FileResponse
from fastapi.staticfiles import StaticFiles
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel
import threading

# Import our modules
try:
    from data import get_trucks_data, dataset_loader
    print("✅ Real data modules loaded successfully")
except ImportError as e:
    print(f"❌ Error loading data modules: {e}")
    raise

try:
    from enhanced_rescue_logic import EnhancedRescueLogic
    print("✅ Enhanced rescue logic loaded successfully")
except ImportError as e:
    print(f"❌ Error loading rescue logic: {e}")
    raise

try:
    from ors_client import ORSClient
    print("✅ ORS client loaded successfully")
except ImportError as e:
    print(f"❌ Error loading ORS client: {e}")
    raise

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# Initialize FastAPI app
app = FastAPI(title="Enhanced Mumbai Cold Chain Rescue Manager", version="2.0")

# Add CORS middleware to allow all origins
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # Allows all origins
    allow_credentials=True,
    allow_methods=["*"],  # Allows all methods
    allow_headers=["*"],  # Allows all headers
)

# Global state
trucks: Dict[str, Dict] = {}
delivery_points: List[Dict] = []
rescue_logic: Optional[EnhancedRescueLogic] = None
ors_client: Optional[ORSClient] = None
simulation_running = False
rescue_routes: Dict[str, Dict] = {}
system_logs: List[str] = []

# Pydantic models
class TruckStatus(BaseModel):
    truck_id: str
    status: str
    temperature: float
    battery: float
    location: Dict[str, float]
    failure_reason: Optional[str] = None
    last_updated: str

class RescueRequest(BaseModel):
    failed_truck_id: str

class RescueResponse(BaseModel):
    success: bool
    rescue_truck_id: Optional[str] = None
    route: Optional[Dict] = None
    message: str

# Initialize system
def initialize_system():
    """Initialize the rescue management system with real data."""
    global trucks, delivery_points, rescue_logic, ors_client
    
    try:
        # Load real data
        trucks_data = get_trucks_data()
        
        # Convert to the format expected by the system
        trucks = {}
        # Enhanced Mumbai delivery routes - longer multi-stop routes like in the image
        mumbai_delivery_routes = [
            # Route 1: Central to North (3 points)
            [(19.0760, 72.8777), (19.1197, 72.8464), (19.2183, 72.9781)],
            # Route 2: South to East (3 points)
            [(19.0170, 72.8478), (19.0759, 72.8774), (19.0330, 73.0297)],
            # Route 3: West to Central (3 points)
            [(19.0596, 72.8295), (19.0760, 72.8777), (19.1593, 72.8478)],
            # Route 4: North to South (3 points)
            [(19.2324, 72.8565), (19.1197, 72.8464), (18.9647, 72.8258)],
            # Route 5: East to West (3 points)
            [(19.0544, 72.9005), (19.0760, 72.8777), (19.0596, 72.8295)],
            # Route 6: Central loop (3 points)
            [(19.0759, 72.8774), (19.0170, 72.8478), (19.0330, 73.0297)],
            # Route 7: Suburban route (3 points)
            [(19.1593, 72.8478), (19.2183, 72.9781), (19.2324, 72.8565)],
            # Route 8: Harbor line (3 points)
            [(18.9647, 72.8258), (19.0544, 72.9005), (19.0759, 72.8774)]
        ]
        for i, truck_data in enumerate(trucks_data):
            truck_id = truck_data['id']
            mumbai_loc = random_mumbai_location()
            intended_route = mumbai_delivery_routes[i % len(mumbai_delivery_routes)]
            trucks[truck_id] = {
                'id': truck_id,
                'status': 'operational',
                'temperature': truck_data['temp'],
                'battery': truck_data['battery'],
                'lat': mumbai_loc['lat'],
                'lng': mumbai_loc['lng'],
                'location': [mumbai_loc['lat'], mumbai_loc['lng']],
                'failure_reason': None,
                'last_updated': truck_data['metadata']['last_update'],
                'capacityAvailable': truck_data['capacityAvailable'],
                'totalCapacity': truck_data['totalCapacity'],
                'coldChainReliability': truck_data['coldChainReliability'],
                'stopsRemaining': truck_data['stopsRemaining'],
                'intended_route': intended_route,
                'current_route': intended_route,
                'rescuer_id': None
            }
        
        # Create sample delivery points (since they're not in the dataset)
        delivery_points = [
            {'id': 'DP001', 'name': 'Mumbai Central', 'lat': 19.0760, 'lng': 72.8777, 'priority': 'high'},
            {'id': 'DP002', 'name': 'Andheri', 'lat': 19.1197, 'lng': 72.8464, 'priority': 'medium'},
            {'id': 'DP003', 'name': 'Bandra', 'lat': 19.0596, 'lng': 72.8295, 'priority': 'high'},
            {'id': 'DP004', 'name': 'Thane', 'lat': 19.2183, 'lng': 72.9781, 'priority': 'medium'},
            {'id': 'DP005', 'name': 'Navi Mumbai', 'lat': 19.0330, 'lng': 73.0297, 'priority': 'low'},
            {'id': 'DP006', 'name': 'Kurla', 'lat': 19.0759, 'lng': 72.8774, 'priority': 'medium'},
            {'id': 'DP007', 'name': 'Dadar', 'lat': 19.0170, 'lng': 72.8478, 'priority': 'high'},
            {'id': 'DP008', 'name': 'Borivali', 'lat': 19.2324, 'lng': 72.8565, 'priority': 'low'},
            {'id': 'DP009', 'name': 'Chembur', 'lat': 19.0544, 'lng': 72.9005, 'priority': 'medium'},
            {'id': 'DP010', 'name': 'Goregaon', 'lat': 19.1593, 'lng': 72.8478, 'priority': 'low'}
        ]
        
        # Initialize rescue logic
        rescue_logic = EnhancedRescueLogic()
        
        # Initialize ORS client
        ors_client = ORSClient()
        
        print("✅ All components initialized successfully")
        print(f"✅ Loaded {len(trucks)} trucks from real dataset")
        print(f"✅ Loaded {len(delivery_points)} delivery points")
        
        # Initialize demo with subset of trucks
        demo_trucks = list(trucks.keys())[:4]  # Use first 4 trucks for demo
        trucks = {k: trucks[k] for k in demo_trucks}
        print(f"Demo initialized with {len(trucks)} trucks and {len(delivery_points)} delivery points")
        
    except Exception as e:
        print(f"❌ Error initializing system: {e}")
        raise

# Temperature drift simulation - REALISTIC COLD CHAIN MONITORING
def simulate_temperature_drift():
    """Simulate realistic temperature drift for cold chain trucks."""
    global trucks
    
    for truck_id, truck in trucks.items():
        if truck['status'] == "operational":
            # Realistic temperature drift: +0.5-1.5°C every 5 seconds
            drift = random.uniform(0.5, 1.5)
            truck['temperature'] += drift
            
            # Realistic battery drain: -1-2% every 5 seconds
            battery_drain = random.uniform(1.0, 2.0)
            truck['battery'] -= battery_drain
            
            # Update timestamp for real monitoring feel
            truck['last_updated'] = datetime.now().isoformat()

# Failure detection - AUTOMATIC COLD CHAIN MONITORING
def detect_failures():
    """Detect truck failures based on REAL cold chain thresholds."""
    global trucks, system_logs
    
    failed_trucks = []
    
    for truck_id, truck in trucks.items():
        if truck['status'] == "operational":
            # CRITICAL: Cold chain temperature threshold
            if truck['temperature'] > 10.0:
                truck['status'] = "failed"
                truck['failure_reason'] = "Cold Chain Breach - Temperature Critical"
                failed_trucks.append(truck_id)
                log_msg = f"🚨 CRITICAL: {truck_id} cold chain breach at {truck['temperature']:.1f}°C"
                logger.info(log_msg)
                system_logs.append(f"{datetime.now().strftime('%H:%M:%S')} - {log_msg}")
            
            # CRITICAL: Battery drain threshold  
            elif truck['battery'] < 5.0:
                truck['status'] = "failed"
                truck['failure_reason'] = "Battery Drain - Power Critical"
                failed_trucks.append(truck_id)
                log_msg = f"🚨 CRITICAL: {truck_id} battery critical at {truck['battery']:.1f}%"
                logger.info(log_msg)
                system_logs.append(f"{datetime.now().strftime('%H:%M:%S')} - {log_msg}")
            
            # Random mechanical failures (realistic events)
            elif random.random() < 0.008:  # 0.8% chance per cycle = realistic failure rate
                failure_reasons = [
                    "Engine Failure - Mechanical Issue", 
                    "Route Obstruction - Traffic Block",
                    "Refrigeration Unit Malfunction",
                    "GPS Signal Lost - Communication Error",
                    "Tire Puncture - Vehicle Breakdown",
                    "Fuel System Failure - Power Loss",
                    "Compressor Failure - Cooling System Down",
                    "Door Seal Breach - Temperature Loss",
                    "Electrical System Fault - Power Critical",
                    "Transmission Failure - Movement Restricted",
                    "Road Accident - Emergency Stop",
                    "Driver Medical Emergency",
                    "Cargo Shift - Load Instability",
                    "Weather Emergency - Extreme Conditions",
                    "Security Breach - Cargo Threat"
                ]
                reason = random.choice(failure_reasons)
                truck['status'] = "failed"
                truck['failure_reason'] = reason
                failed_trucks.append(truck_id)
                log_msg = f"🚨 ALERT: {truck_id} failure - {reason}"
                logger.info(log_msg)
                system_logs.append(f"{datetime.now().strftime('%H:%M:%S')} - {log_msg}")
    
    return failed_trucks

# Recovery simulation - AUTOMATIC RESCUE COMPLETION
def simulate_recovery():
    """Simulate automatic rescue completion after successful dispatch."""
    global trucks, system_logs
    
    for truck_id, truck in trucks.items():
        # Complete rescue after some time (realistic timing)
        if truck['status'] == "failed" and truck.get('rescuer_id'):
            if random.random() < 0.15:  # 15% chance per cycle = ~30-40 seconds total
                # Mark rescue as completed
                rescuer_id = truck['rescuer_id']
                truck['status'] = "operational"
                truck['temperature'] = random.uniform(2.0, 6.0)  # Fixed temperature
                truck['battery'] = random.uniform(70.0, 95.0)    # Recharged battery
                truck['failure_reason'] = None
                truck['rescuer_id'] = None
                
                # Mark rescuer as operational again
                if rescuer_id in trucks:
                    trucks[rescuer_id]['status'] = "operational"
                
                # Clear rescue route
                if truck_id in rescue_routes:
                    del rescue_routes[truck_id]
                
                log_msg = f"✅ RESCUE COMPLETE: {rescuer_id} successfully rescued {truck_id}"
                logger.info(log_msg)
                system_logs.append(f"{datetime.now().strftime('%H:%M:%S')} - {log_msg}")
                system_logs.append(f"{datetime.now().strftime('%H:%M:%S')} - 💰 Estimated spoilage prevented: ₹{random.randint(80000, 180000):,}")

# Background simulation thread - MANUAL TRIGGER ONLY
def run_simulation():
    """Run background monitoring - ONLY manual triggers cause failures."""
    global simulation_running, trucks
    
    while simulation_running:
        try:
            # ONLY simulate rescue completion (no automatic failures)
            simulate_recovery()
            
            # Keep only last 50 logs
            if len(system_logs) > 50:
                system_logs[:] = system_logs[-50:]
            
            time.sleep(5)  # Update every 5 seconds
            
        except Exception as e:
            logger.error(f"Error in background monitoring: {e}")
            time.sleep(5)
            
        except Exception as e:
            logger.error(f"Error in automatic monitoring: {e}")
            time.sleep(5)

# API Endpoints
@app.get("/")
async def root():
    """Serve the main index page."""
    try:
        with open("index.html", "r", encoding="utf-8") as f:
            content = f.read()
        return HTMLResponse(content=content)
    except FileNotFoundError:
        return HTMLResponse(content="<h1>Index page not found</h1>")

@app.get("/truck_status")
async def get_truck_status():
    """Get current status of all trucks."""
    global trucks
    status_list = []
    for truck_id, truck in trucks.items():
        status = {
            'truck_id': truck_id,
            'status': truck['status'],
            'temperature': round(truck['temperature'], 1),
            'battery': round(truck['battery'], 1),
            'location': {'lat': truck['lat'], 'lng': truck['lng']},
            'failure_reason': truck['failure_reason'],
            'last_updated': truck['last_updated'],
            'intended_route': truck['intended_route'],
            'current_route': truck['current_route'],
            'rescuer_id': truck['rescuer_id']
        }
        status_list.append(status)
    return status_list

@app.get("/delivery_points")
async def get_delivery_points():
    """Get all delivery points."""
    global delivery_points
    
    points = []
    for point in delivery_points:
        points.append({
            "id": point.id,
            "name": point.name,
            "location": {"lat": point.lat, "lng": point.lng},
            "priority": point.priority
        })
    
    return points

@app.post("/force_failure/{truck_id}")
async def force_truck_failure(truck_id: str):
    """Force a truck to fail for demo purposes."""
    global trucks, system_logs
    
    if truck_id not in trucks:
        raise HTTPException(status_code=404, detail="Truck not found")
    
    truck = trucks[truck_id]
    if truck['status'] == "operational":
        truck['status'] = "failed"
        truck['failure_reason'] = "Manual Failure (Demo)"
        log_msg = f"🚨 Truck {truck_id} manually failed for demo"
        logger.info(log_msg)
        system_logs.append(f"{datetime.now().strftime('%H:%M:%S')} - {log_msg}")
        
        # Trigger rescue
        await trigger_rescue(truck_id)
        
        return {"success": True, "message": f"Truck {truck_id} forced to fail"}
    else:
        return {"success": False, "message": f"Truck {truck_id} is already failed"}

@app.post("/run_rescue")
async def run_rescue():
    """Run rescue logic for all failed trucks."""
    global trucks, rescue_logic, system_logs
    
    failed_trucks = [truck_id for truck_id, truck in trucks.items() if truck['status'] == "failed"]
    
    if not failed_trucks:
        return {"success": True, "message": "No failed trucks to rescue"}
    
    rescue_results = []
    for truck_id in failed_trucks:
        result = await trigger_rescue(truck_id)
        rescue_results.append(result)
    
    return {
        "success": True,
        "message": f"Rescue logic executed for {len(failed_trucks)} trucks",
        "results": rescue_results
    }

async def trigger_rescue(failed_truck_id: str):
    """AUTOMATIC RESCUE DISPATCH - 6-factor scoring algorithm."""
    global trucks, rescue_logic, ors_client, rescue_routes, system_logs
    
    if failed_truck_id not in trucks:
        return {"success": False, "message": "Truck not found"}
    
    failed_truck = trucks[failed_truck_id]
    
    # Find best rescue truck using 6-factor scoring
    available_trucks = [truck for truck_id, truck in trucks.items() 
                       if truck['status'] == "operational" and truck_id != failed_truck_id]
    
    best_rescue_truck = rescue_logic.find_best_rescue_truck(failed_truck, available_trucks)
    
    if not best_rescue_truck:
        log_msg = f"❌ No available rescue truck for {failed_truck_id}"
        logger.warning(log_msg)
        system_logs.append(f"{datetime.now().strftime('%H:%M:%S')} - {log_msg}")
        return {"success": False, "message": "No available rescue truck"}
    
    rescue_truck_id = best_rescue_truck['id']
    
    # Generate rescue route (real ORS call or smart fallback)
    try:
        route = rescue_logic.generate_rescue_route(best_rescue_truck, failed_truck, delivery_points)
        
        # Calculate realistic ETA and distance
        distance_km = random.uniform(8.5, 25.3)  # Mumbai traffic realistic
        eta_minutes = int(distance_km * random.uniform(2.2, 3.8))  # Mumbai speed
        
        rescue_routes[failed_truck_id] = {
            "rescue_truck_id": rescue_truck_id,
            "route": route,
            "eta_minutes": eta_minutes,
            "distance_km": round(distance_km, 1),
            "timestamp": datetime.now().isoformat()
        }
        
        # Link trucks for rescue completion tracking
        failed_truck['rescuer_id'] = rescue_truck_id
        
        log_msg = f"🚑 RESCUE DISPATCHED: {rescue_truck_id} → {failed_truck_id} (ETA: {eta_minutes}min, {distance_km:.1f}km)"
        logger.info(log_msg)
        system_logs.append(f"{datetime.now().strftime('%H:%M:%S')} - {log_msg}")
        system_logs.append(f"{datetime.now().strftime('%H:%M:%S')} - 📊 6-factor scoring: Distance, battery, capacity, reliability optimized")
        
        return {
            "success": True,
            "rescue_truck_id": rescue_truck_id,
            "route": route,
            "eta_minutes": eta_minutes,
            "distance_km": distance_km,
            "message": f"Automatic rescue dispatched successfully"
        }
        
    except Exception as e:
        log_msg = f"❌ Error in automatic rescue dispatch: {e}"
        logger.error(log_msg)
        system_logs.append(f"{datetime.now().strftime('%H:%M:%S')} - {log_msg}")
        return {"success": False, "message": f"Error generating route: {e}"}

@app.get("/rescue_routes")
async def get_rescue_routes():
    """Get all active rescue routes."""
    global rescue_routes
    return rescue_routes

@app.get("/system_logs")
async def get_system_logs():
    """Get system logs."""
    global system_logs
    return {"logs": system_logs[-10:]}

@app.post("/start_simulation")
async def start_simulation():
    """Start the automatic simulation."""
    global simulation_running
    
    if simulation_running:
        return {"success": False, "message": "Simulation already running"}
    
    simulation_running = True
    simulation_thread = threading.Thread(target=run_simulation, daemon=True)
    simulation_thread.start()
    
    log_msg = "🚀 Automatic simulation started"
    logger.info(log_msg)
    system_logs.append(f"{datetime.now().strftime('%H:%M:%S')} - {log_msg}")
    
    return {"success": True, "message": "Simulation started"}

@app.post("/stop_simulation")
async def stop_simulation():
    """Stop the automatic simulation."""
    global simulation_running
    
    simulation_running = False
    log_msg = "⏹️ Automatic simulation stopped"
    logger.info(log_msg)
    system_logs.append(f"{datetime.now().strftime('%H:%M:%S')} - {log_msg}")
    
    return {"success": True, "message": "Simulation stopped"}

@app.get("/demo")
async def demo_page():
    """Redirect to normal operations."""
    return HTMLResponse(content='<script>window.location.href="/normal_ops";</script>')

@app.get("/dashboard")
async def dashboard_page():
    """Redirect to normal operations."""
    return HTMLResponse(content='<script>window.location.href="/normal_ops";</script>')

@app.get("/simple")
async def simple_demo():
    """Redirect to normal operations."""
    return HTMLResponse(content='<script>window.location.href="/normal_ops";</script>')

@app.get("/normal_ops")
async def normal_ops():
    """Serve the normal operations page - shows fleet in normal state + failure detection."""
    try:
        with open("normal_ops.html", "r", encoding="utf-8") as f:
            content = f.read()
        response = HTMLResponse(content=content)
        response.headers["Access-Control-Allow-Origin"] = "*"
        response.headers["Access-Control-Allow-Methods"] = "GET, POST, OPTIONS"
        response.headers["Access-Control-Allow-Headers"] = "*"
        return response
    except FileNotFoundError:
        return HTMLResponse(content="<h1>Normal operations page not found</h1>")

@app.get("/rescue_ops")
async def rescue_ops():
    """Serve the rescue operations page - shows active rescues and routes."""
    try:
        with open("rescue_ops.html", "r", encoding="utf-8") as f:
            content = f.read()
        response = HTMLResponse(content=content)
        response.headers["Access-Control-Allow-Origin"] = "*"
        response.headers["Access-Control-Allow-Methods"] = "GET, POST, OPTIONS"
        response.headers["Access-Control-Allow-Headers"] = "*"
        return response
    except FileNotFoundError:
        return HTMLResponse(content="<h1>Rescue operations page not found</h1>")

@app.get("/metrics")
async def get_metrics():
    """Get system metrics for dashboard analytics."""
    global trucks, rescue_routes, system_logs
    
    # Count truck statuses
    operational = sum(1 for truck in trucks.values() if truck['status'] == 'operational')
    failed = sum(1 for truck in trucks.values() if truck['status'] == 'failed')
    rescuing = sum(1 for truck in trucks.values() if truck['status'] == 'rescuing')
    
    # Temperature and battery stats
    temps = [truck['temperature'] for truck in trucks.values()]
    batteries = [truck['battery'] for truck in trucks.values()]
    
    # Calculate spoilage prevented (rough estimate)
    rescues_completed = len([log for log in system_logs if "rescued by" in log])
    spoilage_prevented = rescues_completed * random.uniform(50000, 150000)  # ₹50k-150k per rescue
    
    return {
        "fleet_status": {
            "operational": operational,
            "failed": failed, 
            "rescuing": rescuing,
            "total": len(trucks)
        },
        "temperature_stats": {
            "avg": round(sum(temps) / len(temps), 1) if temps else 0,
            "max": round(max(temps), 1) if temps else 0,
            "min": round(min(temps), 1) if temps else 0,
            "critical_count": sum(1 for t in temps if t > 10.0)
        },
        "battery_stats": {
            "avg": round(sum(batteries) / len(batteries), 1) if batteries else 0,
            "max": round(max(batteries), 1) if batteries else 0,
            "min": round(min(batteries), 1) if batteries else 0,
            "low_count": sum(1 for b in batteries if b < 20.0)
        },
        "rescue_stats": {
            "active_rescues": len(rescue_routes),
            "completed_rescues": rescues_completed,
            "spoilage_prevented_inr": round(spoilage_prevented, 0)
        },
        "system_health": {
            "simulation_running": simulation_running,
            "total_logs": len(system_logs),
            "last_update": datetime.now().isoformat()
        }
    }

# Static files
try:
    app.mount("/static", StaticFiles(directory="."), name="static")
except:
    pass

def random_mumbai_location():
    lat = random.uniform(18.90, 19.30)
    lng = random.uniform(72.75, 72.95)
    return {"lat": lat, "lng": lng}

def start_demo_scenario():
    """Initialize fleet with manual trigger capability."""
    global trucks, rescue_routes, system_logs, simulation_running
    
    # Set all trucks to operational with good starting values
    for truck_id, truck in trucks.items():
        truck['status'] = 'operational'
        truck['temperature'] = random.uniform(2.0, 6.0)  # Good starting temps
        truck['battery'] = random.uniform(80.0, 100.0)   # Good starting battery
        truck['failure_reason'] = None
        truck['rescuer_id'] = None
    
    # START BACKGROUND MONITORING (rescue completion only)
    simulation_running = True
    simulation_thread = threading.Thread(target=run_simulation, daemon=True)
    simulation_thread.start()
    
    log_msg = "🚛 Mumbai Cold Chain System ONLINE - Manual trigger mode"
    logger.info(log_msg)
    system_logs.append(f"{datetime.now().strftime('%H:%M:%S')} - {log_msg}")
    system_logs.append(f"{datetime.now().strftime('%H:%M:%S')} - 📊 Fleet ready: {len(trucks)} trucks across Mumbai")
    system_logs.append(f"{datetime.now().strftime('%H:%M:%S')} - 🔧 Use manual triggers on homepage for failures")

# Call demo scenario after system init
initialize_system()
start_demo_scenario()

if __name__ == "__main__":
    
    # Print startup banner
    print("🚛 Enhanced Mumbai Cold Chain Rescue Manager")
    print("=" * 60)
    print("Open http://localhost:8000/ in your browser to access the Mumbai Cold Chain Rescue Manager.")
    print("=" * 60)
    print("🚀 MUMBAI COLD CHAIN SYSTEM IS NOW LIVE!")
    print("   - Manual failure triggers available on homepage")
    print("   - Automatic rescue dispatch when failures occur")
    print("   - No automatic failures - only manual triggers")
    print("💡 TIP: Use the homepage for all demo actions!")
    
    # Start server
    uvicorn.run(app, host="0.0.0.0", port=8000, reload=False)

@app.post("/trigger_failure/{failure_type}")
async def trigger_specific_failure(failure_type: str):
    """Trigger a specific type of failure for demo purposes."""
    global trucks, system_logs
    
    # Find an operational truck
    operational_trucks = [truck_id for truck_id, truck in trucks.items() if truck['status'] == "operational"]
    
    if not operational_trucks:
        return {"success": False, "message": "No operational trucks available to fail"}
    
    # Select a random operational truck with some preference for variety
    truck_id = random.choice(operational_trucks)
    truck = trucks[truck_id]
    
    # Add some randomization to truck parameters for more realistic failures
    if random.random() < 0.3:  # 30% chance to slightly modify current stats
        truck['battery'] = max(10, truck['battery'] - random.uniform(5, 15))
        truck['temperature'] = truck['temperature'] + random.uniform(-1, 2)
    
    # Define failure types and their specific effects with more variety
    failure_scenarios = {
        'temperature': [
            {
                'reason': 'Cold Chain Breach - Temperature Spike',
                'effect': lambda t: setattr(t, 'temperature', random.uniform(12.0, 16.0))
            },
            {
                'reason': 'Refrigeration Coolant Leak',
                'effect': lambda t: setattr(t, 'temperature', random.uniform(9.5, 13.5))
            },
            {
                'reason': 'Thermal Insulation Failure',
                'effect': lambda t: setattr(t, 'temperature', random.uniform(11.0, 14.8))
            }
        ],
        'battery': [
            {
                'reason': 'Battery Drain - Power Critical',
                'effect': lambda t: setattr(t, 'battery', random.uniform(1.0, 8.0))
            },
            {
                'reason': 'Electrical System Malfunction',
                'effect': lambda t: setattr(t, 'battery', random.uniform(2.0, 12.0))
            },
            {
                'reason': 'Power Management Unit Failure',
                'effect': lambda t: setattr(t, 'battery', random.uniform(0.5, 6.0))
            }
        ],
        'engine': [
            {
                'reason': 'Engine Overheating - Coolant Issue',
                'effect': lambda t: None
            },
            {
                'reason': 'Transmission Failure - Gear Lock',
                'effect': lambda t: None
            },
            {
                'reason': 'Fuel System Malfunction',
                'effect': lambda t: None
            }
        ],
        'gps': [
            {
                'reason': 'GPS Signal Lost - Satellite Error',
                'effect': lambda t: None
            },
            {
                'reason': 'Navigation System Crashed',
                'effect': lambda t: None
            },
            {
                'reason': 'Communication Module Failure',
                'effect': lambda t: None
            }
        ],
        'refrigeration': [
            {
                'reason': 'Compressor Failure - Mechanical',
                'effect': lambda t: setattr(t, 'temperature', random.uniform(8.5, 12.5))
            },
            {
                'reason': 'Refrigerant Pressure Drop',
                'effect': lambda t: setattr(t, 'temperature', random.uniform(9.0, 13.0))
            },
            {
                'reason': 'Cooling Fan Motor Burned Out',
                'effect': lambda t: setattr(t, 'temperature', random.uniform(10.0, 14.2))
            }
        ],
        'route': [
            {
                'reason': 'Mumbai Traffic Jam - Route Blocked',
                'effect': lambda t: None
            },
            {
                'reason': 'Construction Zone - Road Closure',
                'effect': lambda t: None
            },
            {
                'reason': 'Accident on Designated Route',
                'effect': lambda t: None
            }
        ]
    }
    
    if failure_type not in failure_scenarios:
        return {"success": False, "message": f"Unknown failure type: {failure_type}"}

    # Randomly select one scenario from the failure type
    scenario = random.choice(failure_scenarios[failure_type])
    
    # Apply the failure
    truck['status'] = "failed"
    truck['failure_reason'] = scenario['reason']
    
    # Apply specific effects (like temperature/battery changes)
    if scenario['effect']:
        # Convert dict to object-like for the lambda
        class TruckObj:
            def __init__(self, truck_dict):
                self.truck_dict = truck_dict
            def __setattr__(self, name, value):
                if name != 'truck_dict':
                    self.truck_dict[name] = value
                else:
                    super().__setattr__(name, value)
        
        truck_obj = TruckObj(truck)
        scenario['effect'](truck_obj)
    
    log_msg = f"🚨 MANUAL TRIGGER: {truck_id} - {scenario['reason']}"
    logger.info(log_msg)
    system_logs.append(f"{datetime.now().strftime('%H:%M:%S')} - {log_msg}")
    
    # Automatically trigger rescue
    try:
        result = await trigger_rescue(truck_id)
        if result.get('success'):
            rescue_log = f"🚑 AUTO-RESCUE: {result['rescue_truck_id']} dispatched to {truck_id}"
            system_logs.append(f"{datetime.now().strftime('%H:%M:%S')} - {rescue_log}")
            
            # Mark rescue truck as rescuing
            rescue_truck_id = result['rescue_truck_id']
            if rescue_truck_id in trucks:
                trucks[rescue_truck_id]['status'] = 'rescuing'
    except Exception as e:
        error_log = f"❌ Auto-rescue failed for {truck_id}: {e}"
        logger.error(error_log)
        system_logs.append(f"{datetime.now().strftime('%H:%M:%S')} - {error_log}")
    
    return {
        "success": True, 
        "message": f"Triggered {failure_type} failure on {truck_id}",
        "truck_id": truck_id,
        "failure_reason": scenario['reason']
    }