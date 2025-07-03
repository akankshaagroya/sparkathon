import json
import os
import pandas as pd
from typing import List, Dict, Any
from datetime import datetime
import logging

logger = logging.getLogger(__name__)

class DatasetLoader:
    def __init__(self, dataset_path="../dataset/output"):
        self.dataset_path = dataset_path
        self.trucks_metadata = None
        self.events_data = None
        self.load_data()
    
    def load_data(self):
        """Load all dataset files"""
        try:
            # Load trucks metadata
            trucks_metadata_path = os.path.join(self.dataset_path, "trucks_metadata.json")
            with open(trucks_metadata_path, 'r') as f:
                self.trucks_metadata = json.load(f)
            
            # Load events data
            events_path = os.path.join(self.dataset_path, "events.json")
            with open(events_path, 'r') as f:
                self.events_data = json.load(f)
            
            logger.info(f"Loaded {len(self.trucks_metadata)} trucks and {len(self.events_data)} events")
        
        except Exception as e:
            logger.error(f"Error loading dataset: {e}")
            self.trucks_metadata = []
            self.events_data = []
    
    def get_latest_truck_status(self) -> List[Dict[str, Any]]:
        """Get the latest status for each truck from events data"""
        if not self.events_data:
            return []
        
        # Group events by truck_id and get the latest event for each truck
        latest_events = {}
        
        for event in self.events_data:
            truck_id = event['truck_id']
            event_time = datetime.fromisoformat(event['timestamp'].replace('Z', '+00:00'))
            
            if truck_id not in latest_events:
                latest_events[truck_id] = event
            else:
                current_time = datetime.fromisoformat(latest_events[truck_id]['timestamp'].replace('Z', '+00:00'))
                if event_time > current_time:
                    latest_events[truck_id] = event
        
        # Combine with metadata to create comprehensive truck status
        trucks = []
        metadata_dict = {truck['truck_id']: truck for truck in self.trucks_metadata}
        
        for truck_id, event in latest_events.items():
            metadata = metadata_dict.get(truck_id, {})
            
            # Calculate available capacity
            total_capacity = metadata.get('total_capacity_kg', 1000)
            used_capacity = metadata.get('used_capacity_kg', 0)
            capacity_available = (total_capacity - used_capacity) / total_capacity
            
            # Determine cold chain reliability based on recent performance
            cold_chain_reliability = self._calculate_cold_chain_reliability(truck_id)
            
            # Count remaining stops (simplified - using random for demo)
            stops_remaining = metadata.get('stops_remaining', 2)
            
            # Generate items list based on truck type and usage
            items = self._generate_items_list(metadata, used_capacity)
            
            truck_status = {
                "id": truck_id,
                "temp": event.get('temperature_c', 0),
                "refrigeration": event.get('refrigeration_status', 'Off') == 'On',
                "battery": event.get('battery_level_percent', 0),
                "location": (event.get('gps_lat', 0), event.get('gps_lon', 0)),
                "capacityAvailable": capacity_available,
                "totalCapacity": 1.0,  # Normalized
                "stopsRemaining": stops_remaining,
                "coldChainReliability": cold_chain_reliability,
                "status": "OK",  # Will be updated by failure detection
                "items": items,
                "metadata": {
                    "truck_type": metadata.get('truck_type', 'unknown'),
                    "region": metadata.get('region_code', 'unknown'),
                    "health_status": metadata.get('truck_health_status', 'unknown'),
                    "total_capacity_kg": total_capacity,
                    "used_capacity_kg": used_capacity,
                    "cold_chain_status": event.get('cold_chain_status', 'UNKNOWN'),
                    "alert_level": event.get('alert_level', 'none'),
                    "last_update": event.get('timestamp')
                }
            }
            
            trucks.append(truck_status)
        
        return trucks
    
    def _calculate_cold_chain_reliability(self, truck_id: str) -> float:
        """Calculate cold chain reliability score for a truck"""
        # Get recent events for this truck
        truck_events = [e for e in self.events_data if e['truck_id'] == truck_id]
        
        if not truck_events:
            return 0.5
        
        # Take last 10 events to calculate reliability
        recent_events = truck_events[-10:]
        
        # Score based on temperature stability, refrigeration uptime, etc.
        score = 0.0
        for event in recent_events:
            temp = event.get('temperature_c', 10)
            refrig_on = event.get('refrigeration_status') == 'On'
            cold_chain_normal = event.get('cold_chain_status') == 'NORMAL'
            
            event_score = 0.0
            if temp <= 8.0:  # Good temperature
                event_score += 0.4
            if refrig_on:  # Refrigeration working
                event_score += 0.3
            if cold_chain_normal:  # Overall cold chain OK
                event_score += 0.3
            
            score += event_score
        
        return min(score / len(recent_events), 1.0)
    
    def _generate_items_list(self, metadata: Dict, used_capacity: float) -> List[str]:
        """Generate a realistic items list based on truck usage and type"""
        if used_capacity == 0:
            return []
        
        # Base items on truck type and capacity usage
        truck_type = metadata.get('truck_type', 'diesel')
        region = metadata.get('region_code', 'IN-CENTRAL')
        
        items = []
        
        # Add items based on capacity usage
        if used_capacity > 100:
            items.extend(['milk', 'dairy'])
        if used_capacity > 200:
            items.extend(['vegetables', 'fruit'])
        if used_capacity > 300:
            items.extend(['meat', 'frozen_goods'])
        if used_capacity > 400:
            items.extend(['beverages', 'ice_cream'])
        
        # Regional variations
        if 'NORTH' in region:
            items.extend(['wheat', 'rice'])
        elif 'SOUTH' in region:
            items.extend(['spices', 'coconut'])
        elif 'WEST' in region:
            items.extend(['cotton', 'sugarcane'])
        elif 'EAST' in region:
            items.extend(['fish', 'jute'])
        
        return list(set(items))  # Remove duplicates
    
    def get_truck_by_id(self, truck_id: str) -> Dict[str, Any]:
        """Get specific truck data by ID"""
        trucks = self.get_latest_truck_status()
        return next((truck for truck in trucks if truck['id'] == truck_id), None)
    
    def get_failed_trucks(self, temp_threshold=8, min_battery=5) -> List[Dict[str, Any]]:
        """Get trucks that meet failure criteria"""
        trucks = self.get_latest_truck_status()
        failed = []
        
        for truck in trucks:
            if (truck['temp'] > temp_threshold or 
                not truck['refrigeration'] or 
                truck['battery'] < min_battery):
                failed.append(truck)
        
        return failed
    
    def refresh_data(self):
        """Reload data from files"""
        self.load_data()
        logger.info("Data refreshed from dataset files")

# Global instance
dataset_loader = DatasetLoader()

def get_trucks_data():
    """Get current trucks data"""
    return dataset_loader.get_latest_truck_status()

def refresh_trucks_data():
    """Refresh trucks data from dataset"""
    dataset_loader.refresh_data()
    return dataset_loader.get_latest_truck_status()

# For backward compatibility, create a trucks list
trucks = get_trucks_data()
