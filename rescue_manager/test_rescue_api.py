#!/usr/bin/env python3
"""
Test script for the Rescue Manager API with real dataset
"""

import requests
import json
import time

BASE_URL = "http://127.0.0.1:8000"

def test_rescue_api():
    print("🚛 Testing Rescue Manager API with Real Dataset")
    print("=" * 60)
    
    # Test 1: Basic API info
    print("\n1️⃣ Testing API Info...")
    try:
        response = requests.get(f"{BASE_URL}/")
        print(f"✅ API Status: {response.status_code}")
        data = response.json()
        print(f"   Message: {data.get('message')}")
        print(f"   Data Source: {data.get('data_source')}")
    except Exception as e:
        print(f"❌ API Info failed: {e}")
    
    # Test 2: Dataset info
    print("\n2️⃣ Testing Dataset Info...")
    try:
        response = requests.get(f"{BASE_URL}/dataset_info")
        data = response.json()
        print(f"✅ Dataset loaded: {data.get('total_trucks')} trucks")
        print(f"   Regions: {data.get('regions')}")
        print(f"   Truck Types: {data.get('truck_types')}")
        print(f"   Sample Truck IDs: {data.get('sample_truck_ids')}")
    except Exception as e:
        print(f"❌ Dataset info failed: {e}")
    
    # Test 3: Truck status
    print("\n3️⃣ Testing Truck Status...")
    try:
        response = requests.get(f"{BASE_URL}/truck_status")
        data = response.json()
        print(f"✅ Truck Status:")
        print(f"   Total Trucks: {data.get('total_trucks')}")
        print(f"   Failed Trucks: {data.get('failed_trucks')}")
        print(f"   Operational Trucks: {data.get('operational_trucks')}")
        print(f"   Data Source: {data.get('data_source')}")
    except Exception as e:
        print(f"❌ Truck status failed: {e}")
    
    # Test 4: Run rescue operations
    print("\n4️⃣ Testing Rescue Operations...")
    try:
        response = requests.get(f"{BASE_URL}/run_rescue")
        data = response.json()
        print(f"✅ Rescue Operations:")
        print(f"   Message: {data.get('message')}")
        print(f"   Total Trucks: {data.get('total_trucks')}")
        print(f"   Failed Trucks: {data.get('failed_trucks')}")
        print(f"   Successful Rescues: {data.get('successful_rescues')}")
        
        # Print rescue operations details
        operations = data.get('rescue_operations', [])
        if operations:
            print(f"\n   📋 Rescue Operations Details:")
            for i, op in enumerate(operations[:3]):  # Show first 3 operations
                print(f"   {i+1}. From: {op.get('fromTruck')} -> To: {op.get('toTruck')}")
                if op.get('rescue'):
                    print(f"      ETA Preserved: {op.get('etaPreserved')}")
                    print(f"      Money Saved: ${op.get('moneySaved')}")
                    print(f"      Items: {op.get('itemsTransferred')}")
                    details = op.get('rescueDetails', {})
                    print(f"      Failure Reasons: {details.get('failureReasons')}")
                    print(f"      Rescue Distance: {details.get('rescueDistance')} km")
                else:
                    print(f"      Reason: {op.get('reason')}")
        else:
            print("   No rescue operations needed - all trucks operational!")
            
    except Exception as e:
        print(f"❌ Rescue operations failed: {e}")
    
    # Test 5: Health check
    print("\n5️⃣ Testing Health Check...")
    try:
        response = requests.get(f"{BASE_URL}/health")
        data = response.json()
        print(f"✅ Health Status: {data.get('status')}")
    except Exception as e:
        print(f"❌ Health check failed: {e}")
    
    print("\n🎉 API Testing Complete!")
    print("=" * 60)

if __name__ == "__main__":
    test_rescue_api()
