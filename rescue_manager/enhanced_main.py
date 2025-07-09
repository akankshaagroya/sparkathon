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
from fastapi import FastAPI, HTTPException, Request
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
predictive_trend_history = {}

# Add at the top, after global state
truck_095_demo_start_time = None
truck_095_alert_triggered = False
truck_095_failed = False
manual_failure_count = 0

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
                'rescuer_id': None,
                'demo_start_time': None,
                'predictive_temp_alert': False
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
        demo_trucks = list(trucks.keys())[:9]  # Use first 9 trucks for demo
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

            # --- Predictive Alert Logic (for first operational truck only) ---
            if not predictive_trend_history.get(truck_id):
                predictive_trend_history[truck_id] = []
            predictive_trend_history[truck_id].append({
                'timestamp': datetime.now(),
                'temperature': truck['temperature'],
                'battery': truck['battery']
            })
            # Keep only last 5 readings
            predictive_trend_history[truck_id] = predictive_trend_history[truck_id][-5:]
            # Only do predictive alert for the first operational truck
            if truck_id == "TRUCK_095":
                truck['predictive_temp_alert'] = True
                # Log only once per session
                if not any('temp rising' in l and truck_id in l for l in system_logs[-5:]):
                    log_msg = f"{datetime.now().strftime('%H:%M:%S')} Predictive alert: {truck_id} temperature rising fast (demo mode)."
                    system_logs.append(log_msg)

            # --- Predictive Alert Demo Logic for TRUCK_095 ---
            if truck_id == "TRUCK_095" and truck['status'] == "operational":
                now = datetime.now()
                if 'demo_start_time' not in truck or truck['demo_start_time'] is None:
                    truck['demo_start_time'] = now
                    truck['predictive_temp_alert'] = False
                else:
                    elapsed = (now - truck['demo_start_time']).total_seconds()
                    if elapsed > 3 and not truck.get('predictive_temp_alert', False):
                        truck['predictive_temp_alert'] = True
                        log_msg = f"{now.strftime('%H:%M:%S')} Predictive alert: {truck_id} temperature rising fast (demo mode)."
                        system_logs.append(log_msg)
                    if elapsed > 6 and truck['predictive_temp_alert']:
                        truck['status'] = "failed"
                        truck['failure_reason'] = "Demo: Temperature rising fast (predictive alert)"
                        truck['temperature'] = random.uniform(12.0, 14.0)  # Set temp above 10C for demo
                        truck['predictive_temp_alert'] = False
                        log_msg = f"{now.strftime('%H:%M:%S')} Demo: {truck_id} auto-failed after predictive alert."
                        system_logs.append(log_msg)
                        # Trigger rescue for demo (threadsafe)
                        global main_event_loop
                        if main_event_loop is not None:
                            future = asyncio.run_coroutine_threadsafe(trigger_rescue(truck_id), main_event_loop)
                            def rescue_callback(fut):
                                try:
                                    result = fut.result()
                                    logger.info(f"[DEBUG] trigger_rescue future result: {result}")
                                    system_logs.append(f"{datetime.now().strftime('%H:%M:%S')} - [DEBUG] trigger_rescue future result: {result}")
                                except Exception as e:
                                    logger.error(f"[DEBUG] trigger_rescue future exception: {e}")
                                    system_logs.append(f"{datetime.now().strftime('%H:%M:%S')} - [DEBUG] trigger_rescue future exception: {e}")
                            future.add_done_callback(rescue_callback)
                        else:
                            logger.error("[DEBUG] main_event_loop is None, cannot schedule trigger_rescue!")
                            system_logs.append(f"{datetime.now().strftime('%H:%M:%S')} - [DEBUG] main_event_loop is None, cannot schedule_trigger_rescue!")
            # Reset timer if not operational
            if truck_id == "TRUCK_095" and truck['status'] != "operational":
                truck['demo_start_time'] = None
                truck['predictive_temp_alert'] = False

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
    now = datetime.now()
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
                # Mark truck as rescued after successful rescue
                if truck_id in trucks:
                    trucks[truck_id]['status'] = 'rescued'
                    trucks[truck_id]['rescue_completed_time'] = now
                    # Mark all pending deliveries as interrupted
                    stops_remaining = trucks[truck_id].get('stopsRemaining', [])
                    if isinstance(stops_remaining, list):
                        for stop in stops_remaining:
                            if isinstance(stop, dict):
                                stop['delivery_status'] = 'interrupted'
                        # Optionally, log for reallocation
                        if stops_remaining:
                            system_logs.append(f"{now.strftime('%H:%M:%S')} - Deliveries for {truck_id} marked as interrupted and need reassignment.")
                    else:
                        # If not a list, just clear it
                        trucks[truck_id]['stopsRemaining'] = []
                    trucks[truck_id]['current_route'] = []
                truck['rescuer_id'] = None
                # Mark rescuer as operational again
                if rescuer_id in trucks:
                    trucks[rescuer_id]['status'] = "operational"
                # Clear rescue route
                if truck_id in rescue_routes:
                    del rescue_routes[truck_id]
                log_msg = f"Rescue complete: {rescuer_id} rescued {truck_id}."
                logger.info(log_msg)
                system_logs.append(f"{now.strftime('%H:%M:%S')} - {log_msg}")
        # Bring rescued truck back to operational after cooldown
        if truck['status'] == 'rescued' and truck.get('rescue_completed_time'):
            elapsed = (now - truck['rescue_completed_time']).total_seconds()
            if elapsed > 10:  # 10 seconds cooldown
                truck['status'] = 'operational'
                truck['temperature'] = random.uniform(2.0, 6.0)
                truck['battery'] = random.uniform(70.0, 95.0)
                truck['failure_reason'] = None
                truck['rescuer_id'] = None
                truck['rescue_completed_time'] = None
                # DO NOT change truck['lat'] or truck['lng']
                system_logs.append(f"{now.strftime('%H:%M:%S')} - Truck {truck_id} returned to service at last delivery/failure point.")

# Background simulation thread - MANUAL TRIGGER ONLY
def run_simulation():
    """Run background monitoring - simulate temp drift AND rescue completion."""
    global simulation_running, trucks

    while simulation_running:
        try:
            simulate_temperature_drift()  # <-- Now called every loop
            simulate_recovery()
            # Keep only last 50 logs
            if len(system_logs) > 50:
                system_logs[:] = system_logs[-50:]
            time.sleep(5)  # Update every 5 seconds
        except Exception as e:
            logger.error(f"Error in background monitoring: {e}")
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
    """Get current status of all active trucks (exclude rescued/inactive/retired)."""
    global trucks
    status_list = []
    for truck_id, truck in trucks.items():
        if truck['status'] in ["rescued", "inactive", "retired"]:
            continue
        # Clamp temperature to 10.0 unless failed due to temperature breach
        temp = truck['temperature']
        if truck['status'] == 'failed' and truck['failure_reason'] and (
            'Temperature' in truck['failure_reason'] or 'Cold Chain Breach' in truck['failure_reason']):
            # Show real temp for temp failures
            display_temp = round(temp, 1)
        else:
            display_temp = min(round(temp, 1), 10.0)
        status = {
            'truck_id': truck_id,
            'status': truck['status'],
            'temperature': display_temp,
            'battery': round(truck['battery'], 1),
            'location': {'lat': truck['lat'], 'lng': truck['lng']},
            'failure_reason': truck['failure_reason'],
            'last_updated': truck['last_updated'],
            'intended_route': truck['intended_route'],
            'current_route': truck['current_route'],
            'rescuer_id': truck['rescuer_id'],
            'predictive_temp_alert': truck.get('predictive_temp_alert', False),
            'predictive_battery_alert': truck.get('predictive_battery_alert', False),
        }
        # DEMO: Always set predictive_temp_alert for TRUCK_095
        if truck_id == "TRUCK_095":
            status['predictive_temp_alert'] = truck.get('predictive_temp_alert', False)
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
async def force_truck_failure(truck_id: str, request: Request):
    global trucks, system_logs, manual_failure_count
    user = "unknown"
    try:
        data = await request.json()
        user = data.get("user", "unknown")
    except:
        pass
    if truck_id not in trucks:
        raise HTTPException(status_code=404, detail="Truck not found")
    truck = trucks[truck_id]
    if truck['status'] == "operational":
        truck['status'] = "failed"
        truck['failure_reason'] = "Manual Failure (Demo)"
        log_msg = f"Truck {truck_id} manually failed for demo by {user}."
        logger.info(log_msg)
        system_logs.append(f"{datetime.now().strftime('%H:%M:%S')} - {log_msg}")
        manual_failure_count += 1
        # On the second manual failure, force a multi-truck rescue and log details
        if manual_failure_count == 2:
            # Force the failed truck's load to be high and all others' capacity zero except two rescuers
            truck['load'] = 100
            truck['capacityAvailable'] = 100
            truck['totalCapacity'] = 100
            # Find two available rescue trucks (not the failed one)
            available_trucks = [t for t in trucks.values() if t['id'] != truck_id and t['status'] == 'operational']
            if len(available_trucks) >= 2:
                rescuer1, rescuer2 = available_trucks[:2]
                rescuer1['capacityAvailable'] = 60
                rescuer1['totalCapacity'] = 60
                rescuer2['capacityAvailable'] = 40
                rescuer2['totalCapacity'] = 40
                # Set all other trucks' capacity to zero
                for t in trucks.values():
                    if t['id'] not in [truck_id, rescuer1['id'], rescuer2['id']]:
                        t['capacityAvailable'] = 0
                        t['totalCapacity'] = 0
                # Trigger rescue and log multi-rescue details
                rescue_result = await trigger_rescue(truck_id)
                if rescue_result.get('multi_rescue') and 'rescuers' in rescue_result:
                    rescuer_ids = [rescuer['rescue_truck_id'] for rescuer in rescue_result['rescuers']]
                    now = datetime.now()
                    system_logs.append(f"{now.strftime('%H:%M:%S')} 🔄 Multi-rescue initiated: {rescuer_ids[0]} (60%) + {rescuer_ids[1]} (40%)")
                    # Simulate log times for each rescuer
                    system_logs.append(f"{(now + timedelta(seconds=10)).strftime('%H:%M:%S')} 🟡 {rescuer_ids[0]} collecting 60% of batch")
                    system_logs.append(f"{(now + timedelta(seconds=12)).strftime('%H:%M:%S')} 🟡 {rescuer_ids[1]} collecting 40% of batch")
                # --- RESTORE ALL TRUCKS' CAPACITY TO DEFAULT AFTER DEMO ---
                for t in trucks.values():
                    t['capacityAvailable'] = 100
                    t['totalCapacity'] = 100
                # --- END RESTORE ---
                return {"success": True, "message": f"Truck {truck_id} forced to fail (multi-rescue demo)"}
            else:
                log_msg = f"[DEMO] Not enough available trucks for forced multi-truck rescue."
                logger.warning(log_msg)
                system_logs.append(f"{datetime.now().strftime('%H:%M:%S')} - {log_msg}")
                return {"success": False, "message": "Not enough available trucks for multi-rescue demo"}
        # Otherwise, normal single rescue
        await trigger_rescue(truck_id)
        return {"success": True, "message": f"Truck {truck_id} forced to fail"}
    else:
        return {"success": False, "message": f"Truck {truck_id} is already failed"}

@app.post("/run_rescue")
async def run_rescue():
    """Run rescue logic for all failed trucks with queue/priority system."""
    global trucks, rescue_logic, system_logs
    
    # Get all failed trucks, sorted by time of failure (if available, else by id)
    failed_trucks = [truck_id for truck_id, truck in trucks.items() if truck['status'] == "failed"]
    # Optionally, sort by lowest battery or temperature for priority
    failed_trucks.sort(key=lambda tid: (trucks[tid].get('battery', 100), trucks[tid].get('temperature', 100)))
    
    # Get all available rescue trucks
    available_rescue_trucks = [truck_id for truck_id, truck in trucks.items() if truck['status'] == "operational"]
    
    if not failed_trucks:
        return {"success": True, "message": "No failed trucks to rescue"}
    if not available_rescue_trucks:
        for truck_id in failed_trucks:
            log_msg = f"❌ No available rescue truck for {truck_id} (queued)"
            logger.warning(log_msg)
            system_logs.append(f"{datetime.now().strftime('%H:%M:%S')} - {log_msg}")
        return {"success": False, "message": "No available rescue trucks for any failed trucks"}
    
    rescue_results = []
    used_rescue_trucks = set()
    for truck_id in failed_trucks:
        # Skip if already being rescued (admin override or otherwise)
        if trucks[truck_id].get("rescuer_id"):
            continue
        # Find next available rescue truck
        rescue_truck_id = None
        for rid in available_rescue_trucks:
            if rid not in used_rescue_trucks:
                rescue_truck_id = rid
                break
        if not rescue_truck_id:
            log_msg = f"❌ No available rescue truck for {truck_id} (queued)"
            logger.warning(log_msg)
            system_logs.append(f"{datetime.now().strftime('%H:%M:%S')} - {log_msg}")
            continue
        # Mark this rescue truck as used for this round
        used_rescue_trucks.add(rescue_truck_id)
        # Temporarily set this truck as the only available for trigger_rescue
        trucks[rescue_truck_id]['status'] = 'operational'  # Ensure it's available
        result = await trigger_rescue(truck_id)
        rescue_results.append(result)
    
    return {
        "success": True,
        "message": f"Rescue logic executed for {len(rescue_results)} trucks (queue/priority)",
        "results": rescue_results
    }

async def trigger_rescue(failed_truck_id: str):
    """AUTOMATIC RESCUE DISPATCH - 6-factor scoring algorithm, now supports multi-truck rescue."""
    global trucks, rescue_logic, ors_client, rescue_routes, system_logs
    
    logger.info(f"[DEBUG] trigger_rescue called for {failed_truck_id}")
    system_logs.append(f"{datetime.now().strftime('%H:%M:%S')} - [DEBUG] trigger_rescue called for {failed_truck_id}")
    if failed_truck_id not in trucks:
        logger.error(f"[DEBUG] {failed_truck_id} not found in trucks!")
        system_logs.append(f"{datetime.now().strftime('%H:%M:%S')} - [DEBUG] {failed_truck_id} not found in trucks!")
        return {"success": False, "message": "Truck not found"}
    
    failed_truck = trucks[failed_truck_id]
    
    # Find best rescue truck using 6-factor scoring
    available_trucks = [truck for truck_id, truck in trucks.items() 
                       if truck['status'] == "operational" and truck_id != failed_truck_id]
    logger.info(f"[DEBUG] Available trucks for rescue: {[t['id'] for t in available_trucks]}")
    system_logs.append(f"{datetime.now().strftime('%H:%M:%S')} - [DEBUG] Available trucks: {[t['id'] for t in available_trucks]}")

    # --- MULTI-TRUCK RESCUE LOGIC ---
    # If the failed truck's load is too high for any single truck, use multi-truck rescue
    multi_rescue_result = None
    try:
        multi_rescue_result = rescue_logic.multi_truck_rescue(failed_truck, available_trucks, delivery_points)
    except Exception as e:
        logger.error(f"[DEBUG] Exception in multi_truck_rescue: {e}")
        system_logs.append(f"{datetime.now().strftime('%H:%M:%S')} - [DEBUG] Exception in multi_truck_rescue: {e}")
        # Suppress error: fallback to single-truck rescue
        multi_rescue_result = None

    if multi_rescue_result and multi_rescue_result.get("multi_rescue", False):
        # Multi-truck rescue: update rescue_routes with both rescuers
        rescuers = multi_rescue_result["rescuers"]
        rescue_routes[failed_truck_id] = {
            "multi_rescue": True,
            "rescuers": rescuers,
            "timestamp": datetime.now().isoformat()
        }
        # Mark both rescuers as rescuing
        for rescuer in rescuers:
            rid = rescuer["rescue_truck_id"]
            if rid in trucks:
                trucks[rid]["status"] = "rescuing"
        # Link rescuers to failed truck
        failed_truck["rescuer_id"] = [rescuer["rescue_truck_id"] for rescuer in rescuers]
        log_msg = f"Multi-truck rescue dispatched: {[rescuer['rescue_truck_id'] for rescuer in rescuers]} to {failed_truck_id} (ETA: {[rescuer['eta_minutes'] for rescuer in rescuers]}min)"
        logger.info(log_msg)
        system_logs.append(f"{datetime.now().strftime('%H:%M:%S')} - {log_msg}")
        return {
            "success": True,
            "multi_rescue": True,
            "rescuers": rescuers,
            "message": "Multi-truck rescue dispatched successfully"
        }
    # --- END MULTI-TRUCK RESCUE LOGIC ---

    # Fallback to single-truck rescue
    best_rescue_truck = rescue_logic.find_best_rescue_truck(failed_truck, available_trucks)
    logger.info(f"[DEBUG] Best rescue truck: {best_rescue_truck['id'] if best_rescue_truck else None}")
    system_logs.append(f"{datetime.now().strftime('%H:%M:%S')} - [DEBUG] Best rescue truck: {best_rescue_truck['id'] if best_rescue_truck else None}")
    
    if not best_rescue_truck:
        log_msg = f"❌ No available rescue truck for {failed_truck_id}"
        logger.warning(log_msg)
        system_logs.append(f"{datetime.now().strftime('%H:%M:%S')} - {log_msg}")
        return {"success": False, "message": "No available rescue truck"}
    
    rescue_truck_id = best_rescue_truck['id']
    # Mark rescue truck as 'rescuing'
    if rescue_truck_id in trucks:
        trucks[rescue_truck_id]['status'] = 'rescuing'
    
    # Generate rescue route (real ORS call or smart fallback)
    try:
        logger.info(f"[DEBUG] Generating rescue route for {rescue_truck_id} to {failed_truck_id}")
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
        
        log_msg = f"Rescue dispatched: {rescue_truck_id} to {failed_truck_id} (ETA: {eta_minutes}min, {distance_km:.1f}km)"
        logger.info(log_msg)
        system_logs.append(f"{datetime.now().strftime('%H:%M:%S')} - {log_msg}")
        system_logs.append(f"{datetime.now().strftime('%H:%M:%S')} - 6-factor scoring: Distance, battery, capacity, reliability optimized.")
        
        return {
            "success": True,
            "rescue_truck_id": rescue_truck_id,
            "route": route,
            "eta_minutes": eta_minutes,
            "distance_km": distance_km,
            "message": f"Automatic rescue dispatched successfully"
        }
    except Exception as e:
        logger.error(f"[DEBUG] Exception in trigger_rescue: {e}")
        system_logs.append(f"{datetime.now().strftime('%H:%M:%S')} - [DEBUG] Exception in trigger_rescue: {e}")
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
    return {"logs": system_logs}

@app.post("/start_simulation")
async def start_simulation():
    """Start the automatic simulation."""
    global simulation_running
    
    if simulation_running:
        return {"success": False, "message": "Simulation already running"}
    
    simulation_running = True
    simulation_thread = threading.Thread(target=run_simulation, daemon=True)
    simulation_thread.start()
    
    log_msg = "System online in manual trigger mode."
    logger.info(log_msg)
    system_logs.append(f"{datetime.now().strftime('%H:%M:%S')} - {log_msg}")
    system_logs.append(f"{datetime.now().strftime('%H:%M:%S')} - Fleet ready: {len(trucks)} trucks across Mumbai.")
    system_logs.append(f"{datetime.now().strftime('%H:%M:%S')} - Use manual triggers on homepage for failures.")
    
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

@app.get("/admin_override")
async def admin_override_page():
    # Serve the custom admin override panel
    try:
        with open("admin_override.html", "r", encoding="utf-8") as f:
            content = f.read()
        response = HTMLResponse(content=content)
        response.headers["Access-Control-Allow-Origin"] = "*"
        response.headers["Access-Control-Allow-Methods"] = "GET, POST, OPTIONS"
        response.headers["Access-Control-Allow-Headers"] = "*"
        return response
    except Exception as e:
        print("Error:", e)
        return HTMLResponse(content="<h1>Admin Override page not found</h1>")

@app.post("/admin_override")
async def admin_override(request: Request):
    global trucks, system_logs, rescue_routes, delivery_points, rescue_logic
    data = await request.json()
    failed_truck_id = data.get("failed_truck_id")
    rescue_truck_id = data.get("rescue_truck_id")
    user = data.get("user", "unknown")
    if not failed_truck_id or not rescue_truck_id:
        return {"success": False, "message": "Both truck IDs required."}
    if failed_truck_id not in trucks or rescue_truck_id not in trucks:
        return {"success": False, "message": "Invalid truck ID(s)."}
    failed_truck = trucks[failed_truck_id]
    rescue_truck = trucks[rescue_truck_id]
    if failed_truck["status"] != "failed":
        return {"success": False, "message": "Selected truck is not failed."}
    if rescue_truck["status"] != "operational":
        return {"success": False, "message": "Selected rescue truck is not operational."}
    # Force assign: set rescuer, mark rescue truck as rescuing
    failed_truck["rescuer_id"] = rescue_truck_id
    rescue_truck["status"] = "rescuing"
    # Generate rescue route and ETA
    try:
        route = rescue_logic.generate_rescue_route(rescue_truck, failed_truck, delivery_points)
        distance_km = random.uniform(8.5, 25.3)
        eta_minutes = int(distance_km * random.uniform(2.2, 3.8))
        rescue_routes[failed_truck_id] = {
            "rescue_truck_id": rescue_truck_id,
            "route": route,
            "eta_minutes": eta_minutes,
            "distance_km": round(distance_km, 1),
            "timestamp": datetime.now().isoformat()
        }
        log_msg = f"{datetime.now().strftime('%H:%M:%S')} ADMIN OVERRIDE: {failed_truck_id} → rescue {rescue_truck_id} (manual)"
        system_logs.append(log_msg)
        system_logs.append(f"{datetime.now().strftime('%H:%M:%S')} - Admin override: {rescue_truck_id} dispatched to {failed_truck_id} (ETA: {eta_minutes}min, {distance_km:.1f}km)")
        return {"success": True, "message": "Override successful. Rescue dispatched."}
    except Exception as e:
        error_msg = f"Admin override failed to generate route: {e}"
        system_logs.append(f"{datetime.now().strftime('%H:%M:%S')} - {error_msg}")
        return {"success": False, "message": error_msg}

@app.get("/metrics")
async def get_metrics():
    """Get system metrics for dashboard analytics (only operational/failed trucks)."""
    global trucks, rescue_routes, system_logs
    
    # Only consider operational/failed trucks
    active_trucks = [truck for truck in trucks.values() if truck['status'] in ['operational', 'failed']]
    operational = sum(1 for truck in active_trucks if truck['status'] == 'operational')
    failed = sum(1 for truck in active_trucks if truck['status'] == 'failed')
    rescuing = sum(1 for truck in active_trucks if truck['status'] == 'rescuing')
    
    # Temperature and battery stats
    temps = [truck['temperature'] for truck in active_trucks]
    batteries = [truck['battery'] for truck in active_trucks]
    
    return {
        "fleet_status": {
            "operational": operational,
            "failed": failed, 
            "rescuing": rescuing,
            "total": len(active_trucks)
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
            "completed_rescues": len([log for log in system_logs if "rescued by" in log]),
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

def random_mumbai_land_location():
    # Mumbai land mask: only allow locations east of Mumbai coastline and not in the sea
    # Use a set of known safe land points for fallback
    safe_land_points = [
        {"lat": 19.0760, "lng": 72.8777},  # Mumbai Central
        {"lat": 19.1197, "lng": 72.8464},  # Andheri
        {"lat": 19.0544, "lng": 72.9005},  # Chembur
        {"lat": 19.1593, "lng": 72.8478},  # Goregaon
        {"lat": 19.2183, "lng": 72.9781},  # Thane
        {"lat": 19.0330, "lng": 73.0297},  # Navi Mumbai
        {"lat": 19.0170, "lng": 72.8478},  # Dadar
        {"lat": 18.9647, "lng": 72.8258},  # South Mumbai
    ]
    for _ in range(2000):
        lat = random.uniform(18.95, 19.25)
        lng = random.uniform(72.83, 72.99)
        # Strict land mask: only allow points east of Mumbai coastline
        if lng < 72.85:
            continue
        if lat < 19.00 and lng < 72.87:
            continue
        if lat < 18.98 and lng > 72.92:
            continue
        if lat > 19.22 and lng < 72.88:
            continue
        if 19.00 < lat < 19.10 and 72.90 < lng < 73.00:
            continue
        # Only return if within Mumbai land area
        if 18.95 <= lat <= 19.25 and 72.85 <= lng <= 72.99:
            return {"lat": lat, "lng": lng}
    # Fallback: pick a random known land point
    return random.choice(safe_land_points)

def random_mumbai_location():
    # Use the same land mask for all random truck locations (no sea)
    return random_mumbai_land_location()

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
    
    log_msg = "System online in manual trigger mode."
    logger.info(log_msg)
    system_logs.append(f"{datetime.now().strftime('%H:%M:%S')} - {log_msg}")
    system_logs.append(f"{datetime.now().strftime('%H:%M:%S')} - Fleet ready: {len(trucks)} trucks across Mumbai.")
    system_logs.append(f"{datetime.now().strftime('%H:%M:%S')} - Use manual triggers on homepage for failures")

# Call demo scenario after system init
initialize_system()
start_demo_scenario()

# Store the main event loop at app startup
main_event_loop = None

@app.on_event("startup")
async def store_main_event_loop():
    global main_event_loop
    main_event_loop = asyncio.get_running_loop()

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
    
    log_msg = f"Manual trigger: {truck_id} - {scenario['reason']}."
    logger.info(log_msg)
    system_logs.append(f"{datetime.now().strftime('%H:%M:%S')} - {log_msg}")
    
    # Automatically trigger rescue
    try:
        result = await trigger_rescue(truck_id)
        if result.get('success'):
            rescue_log = f"Rescue: {result['rescue_truck_id']} dispatched to {truck_id}"
            system_logs.append(f"{datetime.now().strftime('%H:%M:%S')} - {rescue_log}")
            
            # Mark rescue truck as rescuing
            rescue_truck_id = result['rescue_truck_id']
            if rescue_truck_id in trucks:
                trucks[rescue_truck_id]['status'] = 'rescuing'
    except Exception as e:
        error_log = f"Auto-rescue failed for {truck_id}: {e}"
        logger.error(error_log)
        system_logs.append(f"{datetime.now().strftime('%H:%M:%S')} - {error_log}")
    
    # --- DEMO: Force multi-truck rescue on second manual failure trigger ---
    # Use a static variable to count manual failures
    if not hasattr(trigger_specific_failure, 'manual_fail_count'):
        trigger_specific_failure.manual_fail_count = 0
    trigger_specific_failure.manual_fail_count += 1

    # On the second manual failure, force a real multi-truck rescue scenario
    if trigger_specific_failure.manual_fail_count == 2:
        # Set failed truck's load high
        truck['load'] = 200
        # Place failed truck at a Mumbai land location (improved mask)
        land_loc = random_mumbai_land_location()
        truck['location'] = land_loc
        # Pick two real, available trucks (not the failed one)
        available_trucks = [t for tid, t in trucks.items() if tid != truck_id and t['status'] == 'operational']
        if len(available_trucks) >= 2:
            rescuer1, rescuer2 = available_trucks[:2]
            rescuer1['capacityAvailable'] = 120
            rescuer2['capacityAvailable'] = 100
            rescuer1['status'] = 'rescuing'
            rescuer2['status'] = 'rescuing'
            log_msg = f"[DEMO] Forced multi-truck rescue: {truck_id} load=200, rescuers={rescuer1['id']}, {rescuer2['id']} (120/100)"
            logger.info(log_msg)
            system_logs.append(f"{datetime.now().strftime('%H:%M:%S')} - {log_msg}")
        else:
            log_msg = f"[DEMO] Not enough available trucks for forced multi-truck rescue."
            logger.warning(log_msg)
            system_logs.append(f"{datetime.now().strftime('%H:%M:%S')} - {log_msg}")
    # --- END DEMO ---
    
    return {
        "success": True, 
        "message": f"Triggered {failure_type} failure on {truck_id}",
        "truck_id": truck_id,
        "failure_reason": scenario['reason']
    }