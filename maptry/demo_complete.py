#!/usr/bin/env python3
"""
Complete demonstration of the Truck Route Optimizer capabilities.
This script shows all major features working together.
"""

import json
import time
from datetime import datetime
from data_loader import DataLoader
from router import Router
from optimizer import RouteOptimizer
from eta_calculator import ETACalculator
from reassigner import TruckReassigner
from visualizer import RouteVisualizer

def main():
    print("🚚 Comprehensive Truck Route Optimizer Demo")
    print("=" * 60)
    
    # 1. Initialize components
    print("🔧 Initializing components...")
    data_loader = DataLoader()
    router = Router()  # Will use geodesic fallback without API key
    optimizer = RouteOptimizer(router)
    eta_calculator = ETACalculator(router)
    reassigner = TruckReassigner(router, optimizer, eta_calculator)
    visualizer = RouteVisualizer(router)
    
    # 2. Generate sample data
    print("📊 Generating sample data (Mumbai area)...")
    trucks, deliveries = data_loader.generate_sample_data(
        num_trucks=3, 
        num_deliveries=8,
        center_lat=19.0760,  # Mumbai coordinates
        center_lon=72.8777,
        radius_km=20
    )
    
    print(f"   Created {len(trucks)} trucks and {len(deliveries)} delivery points")
    
    # 3. Run initial optimization
    print("⚡ Running initial route optimization...")
    initial_routes = optimizer.optimize_routes(trucks, deliveries, minimize_time=True)
    
    if not initial_routes:
        print("❌ No feasible routes found!")
        return
    
    print(f"   Generated {len(initial_routes)} optimized routes")
    
    # 4. Calculate ETAs
    print("⏰ Calculating estimated times of arrival...")
    etas = eta_calculator.calculate_route_etas(trucks, deliveries, initial_routes)
    
    # 5. Print route summary
    print("\n📋 INITIAL ROUTE OPTIMIZATION RESULTS")
    print("-" * 50)
    
    for route in initial_routes:
        truck = next(t for t in trucks if t.id == route.truck_id)
        print(f"\n🚛 Truck {route.truck_id} (Capacity: {truck.capacity})")
        print(f"   📍 Start: {truck.start}")
        print(f"   📦 Deliveries: {len(route.route)}")
        print(f"   📏 Distance: {route.total_distance_m/1000:.1f} km")
        print(f"   ⏱️  Time: {route.total_time_s/3600:.1f} hours")
        print(f"   📊 Load: {route.total_demand}")
        
        if str(route.truck_id) in etas:
            print("   📅 Schedule:")
            for eta_info in etas[str(route.truck_id)]:
                point = next(p for p in deliveries if p.id == eta_info.point_id)
                print(f"      Point {eta_info.point_id}: {eta_info.eta} "
                      f"(Priority: {point.priority}, Demand: {point.demand})")
    
    # 6. Create initial visualization
    print("\n🗺️ Creating route visualization...")
    route_map = visualizer.create_route_map(trucks, deliveries, initial_routes, etas)
    visualizer.save_map(route_map, "output/demo_initial_routes.html")
    print("   Saved to: output/demo_initial_routes.html")
    
    # 7. Simulate truck failure
    if len(initial_routes) >= 2:
        failed_truck_id = initial_routes[0].truck_id
        print(f"\n🚨 SIMULATING FAILURE OF TRUCK {failed_truck_id}")
        print("-" * 50)
        
        # Simulate truck breakdown at 50% completion
        progress = 0.5
        failed_route = next(r for r in initial_routes if r.truck_id == failed_truck_id)
        completed_deliveries = int(len(failed_route.route) * progress)
        
        print(f"   📍 Truck {failed_truck_id} failed after {completed_deliveries} deliveries")
        print(f"   🔄 Reassigning remaining {len(failed_route.route) - completed_deliveries} deliveries...")
        
        # Run reassignment
        reassignment_result = reassigner.simulate_truck_breakdown(
            trucks, deliveries, initial_routes, failed_truck_id, completed_deliveries
        )
        
        print(f"   ✅ Reassigned {len(reassignment_result.reassigned_points)} delivery points")
        print(f"   🚛 Updated routes for {len(reassignment_result.updated_routes)} trucks")
        
        # Print reassignment summary
        print("\n📋 REASSIGNMENT RESULTS")
        print("-" * 30)
        for truck_id, new_route_indices in reassignment_result.updated_routes.items():
            print(f"   Truck {truck_id}: Now has {len(new_route_indices)} deliveries")
        
        # Create comparison visualization
        print("\n🗺️ Creating before/after comparison map...")
        comparison_map = visualizer.create_comparison_map(
            trucks, deliveries, initial_routes,
            reassignment_result.updated_routes, failed_truck_id
        )
        visualizer.save_map(comparison_map, "output/demo_comparison_map.html")
        print("   Saved to: output/demo_comparison_map.html")
    
    # 8. Performance statistics
    print("\n📊 PERFORMANCE STATISTICS")
    print("-" * 40)
    
    # Initial optimization stats
    stats = optimizer.get_optimization_stats(initial_routes)
    opt_summary = stats['optimization_summary']
    
    print(f"Total Distance: {opt_summary['total_distance_km']:.1f} km")
    print(f"Total Time: {opt_summary['total_time_hours']:.1f} hours")
    print(f"Total Demand: {opt_summary['total_demand']}")
    print(f"Trucks Utilized: {opt_summary['trucks_utilized']}/{opt_summary['trucks_available']}")
    print(f"Utilization Rate: {opt_summary['utilization_rate']}")
    
    # ETA statistics
    total_deliveries = sum(len(truck_etas) for truck_etas in etas.values())
    avg_travel_time = sum(
        eta_info.travel_time_minutes 
        for truck_etas in etas.values() 
        for eta_info in truck_etas
    ) / max(total_deliveries, 1)
    
    print(f"Average Travel Time: {avg_travel_time:.1f} minutes per delivery")
    
    # 9. Save complete results
    print("\n💾 Saving complete results...")
    
    results = {
        "timestamp": datetime.now().isoformat(),
        "trucks": [
            {
                "id": truck.id,
                "start": truck.start,
                "capacity": truck.capacity,
                "speed_kmh": truck.speed_kmh
            }
            for truck in trucks
        ],
        "delivery_points": [
            {
                "id": point.id,
                "location": point.location,
                "demand": point.demand,
                "time_window": f"{point.time_window_start}-{point.time_window_end}",
                "priority": point.priority
            }
            for point in deliveries
        ],
        "initial_routes": [
            {
                "truck_id": route.truck_id,
                "route": route.route,
                "total_distance_km": route.total_distance_m / 1000,
                "total_time_hours": route.total_time_s / 3600,
                "total_demand": route.total_demand
            }
            for route in initial_routes
        ],
        "performance_stats": stats
    }
    
    with open("output/demo_complete_results.json", "w") as f:
        json.dump(results, f, indent=2)
    
    print("   Complete results saved to: output/demo_complete_results.json")
    
    print("\n🎉 DEMONSTRATION COMPLETE!")
    print("=" * 60)
    print("Generated files:")
    print("   📄 output/demo_complete_results.json - Complete optimization data")
    print("   🗺️ output/demo_initial_routes.html - Interactive route map")
    if len(initial_routes) >= 2:
        print("   🗺️ output/demo_comparison_map.html - Before/after failure comparison")
    print("\nOpen the HTML files in your browser to view the interactive maps!")

if __name__ == "__main__":
    main()
