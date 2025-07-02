#!/usr/bin/env python3
"""
Example script showing how to use the Route Optimizer API
"""

import requests
import json
import time

# API Configuration
API_BASE = "http://127.0.0.1:8000"

def test_api():
    """Test the route optimizer API with sample data."""
    
    # Sample data
    trucks = [
        {
            "id": 0,
            "start": [19.0760, 72.8777],
            "capacity": 100,
            "speed_kmh": 40
        },
        {
            "id": 1,
            "start": [19.1000, 72.8500],
            "capacity": 120,
            "speed_kmh": 45
        }
    ]
    
    delivery_points = [
        {
            "id": 100,
            "location": [19.0800, 72.8800],
            "demand": 10,
            "time_window_start": "09:00",
            "time_window_end": "17:00",
            "priority": 2
        },
        {
            "id": 101,
            "location": [19.0900, 72.8600],
            "demand": 15,
            "time_window_start": "10:00",
            "time_window_end": "16:00",
            "priority": 3
        },
        {
            "id": 102,
            "location": [19.0700, 72.8900],
            "demand": 8,
            "time_window_start": "11:00",
            "time_window_end": "15:00",
            "priority": 1
        }
    ]
    
    # Test 1: Health Check
    print("🔍 Testing API health...")
    try:
        response = requests.get(f"{API_BASE}/health")
        print(f"Health check: {response.json()}")
    except requests.exceptions.ConnectionError:
        print("❌ API server is not running. Please start it first:")
        print("python main.py api --port 8000")
        return
    
    # Test 2: Route Optimization
    print("\n🚚 Testing route optimization...")
    
    optimization_request = {
        "trucks": trucks,
        "delivery_points": delivery_points,
        "minimize_time": True
    }
    
    try:
        response = requests.post(
            f"{API_BASE}/optimize",
            json=optimization_request,
            headers={"Content-Type": "application/json"}
        )
        
        if response.status_code == 200:
            result = response.json()
            print("✅ Optimization successful!")
            print(f"Generated {len(result['routes'])} routes:")
            
            for truck_id, route_info in result['routes'].items():
                print(f"  Truck {truck_id}: {route_info['deliveries']} deliveries")
                print(f"    Distance: {route_info['total_distance_km']:.1f} km")
                print(f"    Time: {route_info['total_time_hours']:.1f} hours")
                print(f"    Demand: {route_info['total_demand']}")
                
            print(f"\nETAs for first route:")
            first_truck = list(result['etas'].keys())[0]
            for eta in result['etas'][first_truck]:
                print(f"  Point {eta['point_id']}: {eta['eta']} ({eta['travel_time_minutes']:.1f} min travel)")
                
        else:
            print(f"❌ Optimization failed: {response.status_code}")
            print(response.text)
            
    except Exception as e:
        print(f"❌ Error during optimization: {e}")
    
    # Test 3: Reassignment (requires current routes from optimization)
    print("\n🚨 Testing truck failure reassignment...")
    
    if 'result' in locals() and response.status_code == 200:
        # Convert routes from optimization to the format needed for reassignment
        current_routes = {}
        for truck_id, route_info in result['routes'].items():
            current_routes[int(truck_id)] = [delivery['point_id'] for delivery in route_info['deliveries']]
        
        reassignment_request = {
            "trucks": trucks,
            "delivery_points": delivery_points,
            "current_routes": current_routes,
            "failed_truck_id": 0,
            "current_positions": {
                "0": [19.08, 72.89],  # Current position of failed truck
                "1": [19.09, 72.87]   # Current position of working truck
            }
        }
    
        try:
            response = requests.post(
                f"{API_BASE}/reassign",
                json=reassignment_request,
                headers={"Content-Type": "application/json"}
            )
            
            if response.status_code == 200:
                result = response.json()
                print("✅ Reassignment successful!")
                print(f"Reassigned {len(result['reassigned_points'])} delivery points")
                print(f"Updated routes for {len(result['updated_routes'])} trucks")
                
                for truck_id, new_route in result['updated_routes'].items():
                    print(f"  Truck {truck_id} new route: {len(new_route)} deliveries")
                    
            else:
                print(f"❌ Reassignment failed: {response.status_code}")
                print(response.text)
                
        except Exception as e:
            print(f"❌ Error during reassignment: {e}")
    else:
        print("❌ Skipping reassignment test - optimization failed")

if __name__ == "__main__":
    print("🌐 Testing Truck Route Optimizer API")
    print("=" * 50)
    test_api()
    print("\n🎉 API testing complete!")
