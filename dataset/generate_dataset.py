#!/usr/bin/env python3
"""
Cold Chain Logistics Dataset Generator
Generates synthetic real-time data for refrigerated truck operations
"""

import json
import csv
import random
import datetime
import uuid
import time
import os
from typing import List, Dict, Any
from config import get_config

# Load configuration
CONFIG = get_config()
PRODUCTS = CONFIG["products"]
REGIONS = CONFIG["regions"]

class ColdChainDataGenerator:
    def __init__(self):
        self.trucks = []
        self.events = []
        self.start_time = datetime.datetime.now()
        self.CONFIG = CONFIG
        
    def generate_gps_coordinates_mumbai(self) -> tuple:
        """Generate random GPS coordinates within Mumbai land bounding box only."""
        # Mumbai bounding box (approx): 18.85 <= lat <= 19.35, 72.75 <= lon <= 73.10
        for _ in range(100):  # Try up to 100 times
            lat = random.uniform(18.85, 19.35)
            lon = random.uniform(72.75, 73.10)
            # Optionally, add more precise land mask here
            return round(lat, 6), round(lon, 6)
        # Fallback to center if all else fails
        return 19.0760, 72.8777

    def generate_gps_coordinates(self) -> tuple:
        """Generate random GPS coordinates within Mumbai land bounding box only (overrides global bounds)."""
        return self.generate_gps_coordinates_mumbai()
    
    def generate_delivery_stops(self, num_stops: int = None) -> List[Dict]:
        """Generate delivery stops for a batch"""
        if num_stops is None:
            num_stops = random.randint(1, 4)
        
        stops = []
        base_time = self.start_time + datetime.timedelta(hours=random.randint(1, 48))
        
        for i in range(num_stops):
            lat, lon = self.generate_gps_coordinates()
            eta = base_time + datetime.timedelta(hours=i * random.randint(2, 6))
            
            stops.append({
                "location_name": f"Stop_{uuid.uuid4().hex[:8]}",
                "lat": lat,
                "lon": lon,
                "expected_eta": eta.isoformat(),
                "actual_eta": None,
                "status": "pending"
            })
        
        return stops
    
    def generate_batch(self) -> Dict:
        """Generate a single batch of goods"""
        item_type = random.choice(list(PRODUCTS.keys()))
        perishability = PRODUCTS[item_type]
        
        # Determine temperature requirement based on product
        if item_type in ["ice_cream", "frozen_foods"]:
            temp_req = "frozen"
        elif item_type in ["milk", "meat", "fish", "chicken", "beef", "pork", "vaccines", "blood_products"]:
            temp_req = "refrigerated"
        else:
            temp_req = "refrigerated" if perishability >= 6 else "ambient"
        
        origin_lat, origin_lon = self.generate_gps_coordinates()
        dest_lat, dest_lon = self.generate_gps_coordinates()
        
        return {
            "batch_id": f"BATCH_{uuid.uuid4().hex[:12].upper()}",
            "item_type": item_type,
            "perishability_score": perishability,
            "volume_liters": round(random.uniform(50, 500), 2),
            "weight_kg": round(random.uniform(25, 300), 2),
            "priority_level": random.choice(["High", "Medium", "Low"]),
            "temperature_requirement": temp_req,
            "delivery_stops": self.generate_delivery_stops(),
            "origin_lat": origin_lat,
            "origin_lon": origin_lon,
            "destination_lat": dest_lat,
            "destination_lon": dest_lon
        }
    
    def generate_truck(self, truck_id: str) -> Dict:
        """Generate a single truck with metadata"""
        truck_type = random.choice(["electric", "diesel"])
        total_capacity = random.uniform(1000, 5000)
        
        # Generate batches for this truck
        batch_range = CONFIG["batch_config"]["per_truck_range"]
        num_batches = random.randint(batch_range[0], batch_range[1])
        batches = [self.generate_batch() for _ in range(num_batches)]
        used_capacity = sum(batch["weight_kg"] for batch in batches)
        
        # Ensure used capacity doesn't exceed total
        if used_capacity > total_capacity:
            used_capacity = total_capacity * random.uniform(0.7, 0.9)
        
        last_maintenance = self.start_time - datetime.timedelta(days=random.randint(1, 90))
        
        return {
            "truck_id": truck_id,
            "total_capacity_kg": round(total_capacity, 2),
            "used_capacity_kg": round(used_capacity, 2),
            "last_maintenance_date": last_maintenance.date().isoformat(),
            "truck_os_version": f"v{random.randint(1, 5)}.{random.randint(0, 9)}.{random.randint(0, 9)}",
            "region_code": random.choice(REGIONS),
            "truck_health_status": random.choice(["Healthy", "Rescuing", "Broken Down"]),
            "truck_type": truck_type,
            "batches": batches
        }
    
    def determine_cold_chain_status(self, temperature: float, refrigeration_status: str, 
                                  truck: Dict) -> str:
        """Determine cold chain status based on temperature and truck cargo"""
        # Get the most restrictive temperature requirement from batches
        temp_requirements = [batch["temperature_requirement"] for batch in truck["batches"]]
        
        if "frozen" in temp_requirements:
            target_range = CONFIG["temperature_ranges"]["frozen"]
        elif "refrigerated" in temp_requirements:
            target_range = CONFIG["temperature_ranges"]["refrigerated"]
        else:
            target_range = CONFIG["temperature_ranges"]["ambient"]
        
        if refrigeration_status == "Off":
            return "BREACH"
        elif target_range[0] <= temperature <= target_range[1]:
            return "NORMAL"
        elif temperature < target_range[0]:
            return "OVERCOOLED"
        else:
            return "BREACH"
    
    def inject_fault_scenario(self, event: Dict, truck: Dict) -> Dict:
        """Inject various fault scenarios into events"""
        fault_type = random.choice([
            "cold_chain_breach", "engine_stall", "low_battery", 
            "rescuing_mode", "shock_event", "none"
        ])
        
        if fault_type == "cold_chain_breach":
            event["refrigeration_status"] = "Off"
            event["temperature_c"] = round(random.uniform(15, 30), 2)
            event["cold_chain_status"] = "BREACH"
            event["event_type"] = "fault"
            event["alert_level"] = "high"
            
        elif fault_type == "engine_stall":
            event["engine_status"] = "Stalled"
            event["event_type"] = "fault"
            event["alert_level"] = "high"
            
        elif fault_type == "low_battery":
            event["battery_level_percent"] = round(random.uniform(1, 4), 2)
            event["event_type"] = "fault"
            event["alert_level"] = "medium"
            
        elif fault_type == "rescuing_mode":
            truck["truck_health_status"] = "Rescuing"
            event["event_type"] = "rescuing"
            event["alert_level"] = "medium"
            
        elif fault_type == "shock_event":
            event["shock_event"] = True
            event["event_type"] = "shock"
            event["alert_level"] = "low"
        
        return event
    
    def generate_event(self, truck: Dict, timestamp: datetime.datetime) -> Dict:
        """Generate a single event record for a truck"""
        lat, lon = self.generate_gps_coordinates()
        
        # Base temperature based on truck's cargo requirements
        temp_requirements = [batch["temperature_requirement"] for batch in truck["batches"]]
        if "frozen" in temp_requirements:
            base_temp_range = CONFIG["temperature_ranges"]["frozen"]
        elif "refrigerated" in temp_requirements:
            base_temp_range = CONFIG["temperature_ranges"]["refrigerated"]
        else:
            base_temp_range = CONFIG["temperature_ranges"]["ambient"]
        
        temperature = random.uniform(base_temp_range[0] - 2, base_temp_range[1] + 2)
        refrigeration_status = random.choice(["On", "Off"]) if random.random() > 0.9 else "On"
        
        event = {
            "truck_id": truck["truck_id"],
            "timestamp": timestamp.isoformat(),
            "gps_lat": lat,
            "gps_lon": lon,
            "temperature_c": round(temperature, 2),
            "humidity_percent": round(random.uniform(40, 80), 2),
            "battery_level_percent": round(random.uniform(10, 100), 2),
            "shock_event": random.random() < 0.05,
            "refrigeration_status": refrigeration_status,
            "cold_chain_status": "",  # Will be determined
            "engine_status": random.choice(["On", "Off", "Stalled"]) if random.random() > 0.95 else "On",
            "event_type": "normal",
            "alert_level": "none"
        }
        
        # Add EV-specific fields
        if truck["truck_type"] == "electric":
            event["nearby_charger_available"] = random.choice([True, False])
            event["distance_to_next_charger_km"] = round(random.uniform(5, 50), 2)
        else:
            event["nearby_charger_available"] = None
            event["distance_to_next_charger_km"] = None
        
        # Determine cold chain status
        event["cold_chain_status"] = self.determine_cold_chain_status(
            event["temperature_c"], event["refrigeration_status"], truck
        )
        
        # Inject faults (10% chance)
        if random.random() < 0.1:
            event = self.inject_fault_scenario(event, truck)
        
        return event
    
    def generate_trucks(self):
        """Generate all trucks"""
        print("Generating trucks...")
        for i in range(CONFIG["num_trucks"]):
            truck_id = f"TRUCK_{i+1:03d}"
            truck = self.generate_truck(truck_id)
            self.trucks.append(truck)
        print(f"Generated {len(self.trucks)} trucks")
    
    def generate_events(self):
        """Generate all events"""
        print("Generating events...")
        events_per_truck = CONFIG["num_events"] // CONFIG["num_trucks"]
        time_interval = CONFIG["simulation_duration_hours"] * 3600 // events_per_truck
        
        for truck in self.trucks:
            for i in range(events_per_truck):
                timestamp = self.start_time + datetime.timedelta(
                    seconds=i * time_interval + random.randint(0, time_interval)
                )
                event = self.generate_event(truck, timestamp)
                self.events.append(event)
        
        # Generate additional events to reach target
        remaining_events = CONFIG["num_events"] - len(self.events)
        for _ in range(remaining_events):
            truck = random.choice(self.trucks)
            timestamp = self.start_time + datetime.timedelta(
                seconds=random.randint(0, CONFIG["simulation_duration_hours"] * 3600)
            )
            event = self.generate_event(truck, timestamp)
            self.events.append(event)
        
        # Sort events by timestamp
        self.events.sort(key=lambda x: x["timestamp"])
        print(f"Generated {len(self.events)} events")
    
    def save_to_csv(self):
        """Save data to CSV files"""
        output_dir = CONFIG["output_dir"]
        os.makedirs(output_dir, exist_ok=True)
        
        # Save trucks metadata
        trucks_data = []
        for truck in self.trucks:
            truck_csv = truck.copy()
            # Flatten batches for CSV
            truck_csv['num_batches'] = len(truck["batches"])
            truck_csv['batch_ids'] = ','.join([batch["batch_id"] for batch in truck["batches"]])
            truck_csv['item_types'] = ','.join([batch["item_type"] for batch in truck["batches"]])
            del truck_csv['batches']
            trucks_data.append(truck_csv)
        
        # Write trucks CSV
        with open(f"{output_dir}/trucks_metadata.csv", 'w', newline='') as f:
            if trucks_data:
                writer = csv.DictWriter(f, fieldnames=trucks_data[0].keys())
                writer.writeheader()
                writer.writerows(trucks_data)
        
        # Save events CSV
        with open(f"{output_dir}/events.csv", 'w', newline='') as f:
            if self.events:
                writer = csv.DictWriter(f, fieldnames=self.events[0].keys())
                writer.writeheader()
                writer.writerows(self.events)
        
        # Save batches CSV
        batches_data = []
        for truck in self.trucks:
            for batch in truck["batches"]:
                batch_csv = batch.copy()
                batch_csv['truck_id'] = truck["truck_id"]
                # Flatten delivery stops
                batch_csv['num_stops'] = len(batch["delivery_stops"])
                batch_csv['stop_locations'] = ','.join([stop["location_name"] for stop in batch["delivery_stops"]])
                del batch_csv['delivery_stops']
                batches_data.append(batch_csv)
        
        with open(f"{output_dir}/batches.csv", 'w', newline='') as f:
            if batches_data:
                writer = csv.DictWriter(f, fieldnames=batches_data[0].keys())
                writer.writeheader()
                writer.writerows(batches_data)
        
        print(f"CSV files saved to {output_dir}/")
    
    def save_to_json(self):
        """Save data to JSON files"""
        output_dir = CONFIG["output_dir"]
        os.makedirs(output_dir, exist_ok=True)
        
        # Save complete dataset as JSON
        dataset = {
            "metadata": {
                "generated_at": datetime.datetime.now().isoformat(),
                "num_trucks": len(self.trucks),
                "num_events": len(self.events),
                "simulation_duration_hours": CONFIG["simulation_duration_hours"],
                "gps_bounds": CONFIG["gps_bounds"]
            },
            "trucks": self.trucks,
            "events": self.events
        }
        
        with open(f"{output_dir}/complete_dataset.json", 'w') as f:
            json.dump(dataset, f, indent=2, default=str)
        
        # Save separate files
        with open(f"{output_dir}/trucks_metadata.json", 'w') as f:
            json.dump(self.trucks, f, indent=2, default=str)
        
        with open(f"{output_dir}/events.json", 'w') as f:
            json.dump(self.events, f, indent=2, default=str)
        
        print(f"JSON files saved to {output_dir}/")
    
    def generate_dataset(self):
        """Main method to generate complete dataset"""
        print("Starting cold chain dataset generation...")
        print(f"Target: {CONFIG['num_trucks']} trucks, {CONFIG['num_events']} events")
        
        self.generate_trucks()
        self.generate_events()
        
        print("Saving to files...")
        self.save_to_csv()
        self.save_to_json()
        
        print("Dataset generation completed!")
        print(f"Files saved in '{CONFIG['output_dir']}' directory")
        
        # Print summary statistics
        self.print_summary()
    
    def print_summary(self):
        """Print dataset summary statistics"""
        print("\n" + "="*50)
        print("DATASET SUMMARY")
        print("="*50)
        
        print(f"Total Trucks: {len(self.trucks)}")
        print(f"Total Events: {len(self.events)}")
        
        # Truck health status distribution
        health_dist = {}
        for truck in self.trucks:
            health_dist[truck["truck_health_status"]] = health_dist.get(truck["truck_health_status"], 0) + 1
        print(f"Truck Health Distribution: {health_dist}")
        
        # Event types distribution
        event_types = {}
        for event in self.events:
            event_types[event["event_type"]] = event_types.get(event["event_type"], 0) + 1
        print(f"Event Types Distribution: {event_types}")
        
        # Cold chain status distribution
        cold_chain_dist = {}
        for event in self.events:
            cold_chain_dist[event["cold_chain_status"]] = cold_chain_dist.get(event["cold_chain_status"], 0) + 1
        print(f"Cold Chain Status Distribution: {cold_chain_dist}")
        
        # Product types
        product_types = {}
        for truck in self.trucks:
            for batch in truck["batches"]:
                product_types[batch["item_type"]] = product_types.get(batch["item_type"], 0) + 1
        print(f"Top 10 Product Types: {dict(sorted(product_types.items(), key=lambda x: x[1], reverse=True)[:10])}")

def main():
    """Main execution function"""
    generator = ColdChainDataGenerator()
    generator.generate_dataset()

if __name__ == "__main__":
    main()