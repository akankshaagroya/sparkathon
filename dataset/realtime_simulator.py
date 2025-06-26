#!/usr/bin/env python3
"""
Real-time Cold Chain Logistics Simulator
Simulates real-time streaming of cold chain events
"""

import json
import csv
import time
import datetime
from generate_dataset import ColdChainDataGenerator, CONFIG
import threading
import queue

class RealTimeSimulator:
    def __init__(self, speed_multiplier=1.0):
        """
        Initialize the real-time simulator
        
        Args:
            speed_multiplier: How fast to run simulation (1.0 = real-time, 2.0 = 2x speed)
        """
        self.speed_multiplier = speed_multiplier
        self.generator = ColdChainDataGenerator()
        self.event_queue = queue.Queue()
        self.is_running = False
        
    def generate_initial_data(self):
        """Generate the initial dataset"""
        print("Generating initial dataset...")
        self.generator.generate_trucks()
        self.generator.generate_events()
        print(f"Generated {len(self.generator.events)} events for streaming")
        
    def start_simulation(self, output_callback=None):
        """
        Start the real-time simulation
        
        Args:
            output_callback: Function to call with each event (event_data)
        """
        if not self.generator.events:
            self.generate_initial_data()
            
        self.is_running = True
        start_time = datetime.datetime.now()
        simulation_start_time = datetime.datetime.fromisoformat(self.generator.events[0]["timestamp"])
        
        print(f"Starting real-time simulation with {self.speed_multiplier}x speed multiplier")
        print("Press Ctrl+C to stop the simulation")
        
        try:
            for event in self.generator.events:
                if not self.is_running:
                    break
                    
                # Calculate when this event should be emitted
                event_time = datetime.datetime.fromisoformat(event["timestamp"])
                time_since_start = (event_time - simulation_start_time).total_seconds()
                target_time = start_time + datetime.timedelta(seconds=time_since_start / self.speed_multiplier)
                
                # Wait until it's time to emit this event
                now = datetime.datetime.now()
                if target_time > now:
                    sleep_time = (target_time - now).total_seconds()
                    time.sleep(sleep_time)
                
                # Emit the event
                event_with_realtime = event.copy()
                event_with_realtime["realtime_timestamp"] = datetime.datetime.now().isoformat()
                
                if output_callback:
                    output_callback(event_with_realtime)
                else:
                    self.default_output(event_with_realtime)
                    
        except KeyboardInterrupt:
            print("\nSimulation stopped by user")
        finally:
            self.is_running = False
            
    def stop_simulation(self):
        """Stop the simulation"""
        self.is_running = False
        
    def default_output(self, event):
        """Default output handler - prints to console"""
        alert_indicator = "🚨" if event["alert_level"] == "high" else "⚠️" if event["alert_level"] == "medium" else "📍"
        
        print(f"{alert_indicator} {event['truck_id']} | "
              f"Temp: {event['temperature_c']}°C | "
              f"Status: {event['cold_chain_status']} | "
              f"Location: ({event['gps_lat']:.3f}, {event['gps_lon']:.3f}) | "
              f"Battery: {event['battery_level_percent']}%")
              
    def save_to_realtime_csv(self, filename="output/realtime_events.csv"):
        """Save events to CSV as they're generated in real-time"""
        import os
        os.makedirs(os.path.dirname(filename), exist_ok=True)
        
        def csv_callback(event):
            file_exists = os.path.exists(filename)
            with open(filename, 'a', newline='') as f:
                writer = csv.DictWriter(f, fieldnames=event.keys())
                if not file_exists:
                    writer.writeheader()
                writer.writerow(event)
            self.default_output(event)
            
        return csv_callback
        
    def save_to_realtime_json(self, filename="output/realtime_events.json"):
        """Save events to JSON as they're generated in real-time"""
        import os
        os.makedirs(os.path.dirname(filename), exist_ok=True)
        
        events_list = []
        
        def json_callback(event):
            events_list.append(event)
            with open(filename, 'w') as f:
                json.dump(events_list, f, indent=2, default=str)
            self.default_output(event)
            
        return json_callback

def main():
    """Main function for real-time simulation"""
    import argparse
    
    parser = argparse.ArgumentParser(description="Cold Chain Real-time Simulator")
    parser.add_argument("--speed", type=float, default=1.0, 
                       help="Speed multiplier (1.0 = real-time, 2.0 = 2x speed)")
    parser.add_argument("--output-csv", 
                       help="Save events to CSV file in real-time")
    parser.add_argument("--output-json", 
                       help="Save events to JSON file in real-time")
    
    args = parser.parse_args()
    
    simulator = RealTimeSimulator(speed_multiplier=args.speed)
    
    # Set up output callback
    callback = None
    if args.output_csv:
        callback = simulator.save_to_realtime_csv(args.output_csv)
    elif args.output_json:
        callback = simulator.save_to_realtime_json(args.output_json)
        
    simulator.start_simulation(output_callback=callback)

if __name__ == "__main__":
    main() 