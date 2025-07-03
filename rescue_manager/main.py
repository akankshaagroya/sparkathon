from fastapi import FastAPI, HTTPException
from fastapi.responses import JSONResponse
from pydantic import BaseModel
from typing import List, Dict, Any
import time
import json
import os
from datetime import datetime

from data import get_trucks_data, refresh_trucks_data
from rescue_logic import detect_failures, find_best_rescue, create_rescue_payload
import logging

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

app = FastAPI(
    title="Rescue Manager API",
    description="Cold chain truck rescue management system using real dataset",
    version="1.0.0"
)

# Ensure logs directory exists
os.makedirs("logs", exist_ok=True)

class TruckData(BaseModel):
    id: str
    temp: float
    refrigeration: bool
    battery: int
    location: tuple
    capacityAvailable: float
    totalCapacity: float
    stopsRemaining: int
    coldChainReliability: float
    status: str
    items: List[str]

@app.get("/", response_model=Dict[str, str])
async def root():
    """Root endpoint with API information"""
    return {
        "message": "Rescue Manager API - Using Real Dataset",
        "version": "1.0.0",
        "data_source": "dataset/output/*.json",
        "endpoints": {
            "run_rescue": "/run_rescue",
            "truck_status": "/truck_status",
            "refresh_data": "/refresh_data",
            "health": "/health"
        }
    }

@app.get("/health")
async def health_check():
    """Health check endpoint"""
    return {"status": "healthy", "timestamp": int(time.time())}

@app.get("/refresh_data")
async def refresh_data():
    """Refresh truck data from dataset files"""
    try:
        trucks = refresh_trucks_data()
        logger.info(f"Data refreshed successfully. Loaded {len(trucks)} trucks.")
        return {
            "message": f"Data refreshed successfully. Loaded {len(trucks)} trucks.",
            "timestamp": int(time.time()),
            "trucks_loaded": len(trucks)
        }
    except Exception as e:
        logger.error(f"Error refreshing data: {str(e)}")
        raise HTTPException(status_code=500, detail=str(e))

@app.get("/truck_status")
async def get_truck_status():
    """Get current status of all trucks"""
    try:
        # Get fresh data from dataset
        truck_data = get_trucks_data()
        
        # Detect failures without modifying original data
        truck_data_copy = [truck.copy() for truck in truck_data]
        failed_trucks = detect_failures(truck_data_copy)
        
        # Separate trucks by status
        failed_ids = [truck['id'] for truck in failed_trucks]
        ok_trucks = [truck for truck in truck_data if truck['id'] not in failed_ids]
        
        return {
            "total_trucks": len(truck_data),
            "failed_trucks": len(failed_trucks),
            "operational_trucks": len(ok_trucks),
            "data_source": "Real dataset from dataset/output/",
            "trucks": {
                "failed": failed_trucks,
                "operational": ok_trucks
            },
            "timestamp": int(time.time())
        }
    except Exception as e:
        logger.error(f"Error in get_truck_status: {str(e)}")
        raise HTTPException(status_code=500, detail=str(e))

@app.get("/run_rescue")
async def run_rescue():
    """
    Main rescue operation endpoint
    Detects failed trucks and assigns rescue operations using real dataset
    """
    try:
        # Get fresh data from dataset
        truck_data = get_trucks_data()
        
        if not truck_data:
            return {
                "message": "No truck data available. Please refresh data first.",
                "failed_trucks": 0,
                "rescue_operations": [],
                "timestamp": int(time.time())
            }
        
        # Create a copy to avoid modifying original data
        truck_data_copy = [truck.copy() for truck in truck_data]
        
        # Detect failed trucks
        failed_trucks = detect_failures(truck_data_copy)
        
        if not failed_trucks:
            logger.info("No failed trucks detected in real dataset")
            return {
                "message": "No rescue operations needed",
                "failed_trucks": 0,
                "rescue_operations": [],
                "data_source": "Real dataset from dataset/output/",
                "timestamp": int(time.time())
            }
        
        # Find rescue operations for each failed truck
        rescue_operations = []
        current_timestamp = int(time.time())
        
        for failed_truck in failed_trucks:
            logger.info(f"Processing rescue for truck {failed_truck['id']}")
            
            # Find best rescue truck
            rescue_truck = find_best_rescue(failed_truck, truck_data_copy)
            
            if rescue_truck:
                # Create rescue payload
                rescue_payload = create_rescue_payload(failed_truck, rescue_truck, current_timestamp)
                rescue_operations.append(rescue_payload)
                
                # Log successful rescue assignment
                logger.info(f"Rescue assigned: {failed_truck['id']} -> {rescue_truck['id']}")
                
                # Mark rescue truck as assigned (to avoid double assignment)
                rescue_truck['status'] = 'ASSIGNED'
            else:
                # No rescue truck available
                logger.warning(f"No rescue truck available for {failed_truck['id']}")
                rescue_operations.append({
                    "rescue": False,
                    "fromTruck": failed_truck['id'],
                    "toTruck": None,
                    "reason": "No suitable rescue truck available",
                    "timestamp": current_timestamp
                })
        
        # Save rescue operations to log file
        log_data = {
            "timestamp": current_timestamp,
            "datetime": datetime.now().isoformat(),
            "data_source": "Real dataset from dataset/output/",
            "total_trucks": len(truck_data),
            "failed_trucks_count": len(failed_trucks),
            "successful_rescues": len([op for op in rescue_operations if op.get('rescue', False)]),
            "operations": rescue_operations
        }
        
        log_filename = f"logs/rescue_log_{current_timestamp}.json"
        with open(log_filename, 'w') as f:
            json.dump(log_data, f, indent=2)
        
        logger.info(f"Rescue operations saved to {log_filename}")
        
        # Return results
        return {
            "message": f"Processed {len(failed_trucks)} failed trucks from real dataset",
            "data_source": "Real dataset from dataset/output/",
            "total_trucks": len(truck_data),
            "failed_trucks": len(failed_trucks),
            "successful_rescues": len([op for op in rescue_operations if op.get('rescue', False)]),
            "rescue_operations": rescue_operations,
            "timestamp": current_timestamp
        }
        
    except Exception as e:
        logger.error(f"Error in run_rescue: {str(e)}")
        raise HTTPException(status_code=500, detail=str(e))

@app.post("/update_truck_data")
async def update_truck_data(new_trucks: List[TruckData]):
    """
    Update truck data with new information
    Note: This will override the dataset data temporarily
    """
    try:
        # This would update the in-memory data only
        # In a real system, you'd want to save this back to the dataset
        logger.info(f"Received update request for {len(new_trucks)} trucks")
        
        return {
            "message": f"Update request received for {len(new_trucks)} trucks",
            "note": "This endpoint would update the dataset in a production system",
            "timestamp": int(time.time())
        }
    except Exception as e:
        logger.error(f"Error updating truck data: {str(e)}")
        raise HTTPException(status_code=500, detail=str(e))

@app.get("/logs/{log_id}")
async def get_rescue_log(log_id: str):
    """Get specific rescue operation log"""
    try:
        log_filename = f"logs/rescue_log_{log_id}.json"
        if not os.path.exists(log_filename):
            raise HTTPException(status_code=404, detail="Log not found")
        
        with open(log_filename, 'r') as f:
            log_data = json.load(f)
        
        return log_data
    except Exception as e:
        logger.error(f"Error retrieving log: {str(e)}")
        raise HTTPException(status_code=500, detail=str(e))

@app.get("/logs")
async def list_rescue_logs():
    """List all available rescue operation logs"""
    try:
        if not os.path.exists("logs"):
            return {"logs": []}
        
        log_files = [f for f in os.listdir("logs") if f.startswith("rescue_log_") and f.endswith(".json")]
        
        logs = []
        for log_file in log_files:
            log_id = log_file.replace("rescue_log_", "").replace(".json", "")
            logs.append({
                "log_id": log_id,
                "filename": log_file,
                "timestamp": int(log_id) if log_id.isdigit() else 0
            })
        
        # Sort by timestamp (newest first)
        logs.sort(key=lambda x: x['timestamp'], reverse=True)
        
        return {"logs": logs}
    except Exception as e:
        logger.error(f"Error listing logs: {str(e)}")
        raise HTTPException(status_code=500, detail=str(e))

@app.get("/dataset_info")
async def get_dataset_info():
    """Get information about the loaded dataset"""
    try:
        trucks = get_trucks_data()
        
        if not trucks:
            return {"message": "No data loaded. Please refresh data first."}
        
        # Analyze dataset
        regions = set()
        truck_types = set()
        health_statuses = set()
        
        for truck in trucks:
            metadata = truck.get('metadata', {})
            regions.add(metadata.get('region', 'unknown'))
            truck_types.add(metadata.get('truck_type', 'unknown'))
            health_statuses.add(metadata.get('health_status', 'unknown'))
        
        return {
            "total_trucks": len(trucks),
            "regions": list(regions),
            "truck_types": list(truck_types),
            "health_statuses": list(health_statuses),
            "data_source": "dataset/output/",
            "sample_truck_ids": [truck['id'] for truck in trucks[:5]],
            "timestamp": int(time.time())
        }
    except Exception as e:
        logger.error(f"Error getting dataset info: {str(e)}")
        raise HTTPException(status_code=500, detail=str(e))

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8000)
