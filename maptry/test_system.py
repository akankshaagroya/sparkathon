"""
Test script to verify the route optimization system works.
Can be run without external API dependencies for basic testing.
"""

import sys
import os
import json
from datetime import datetime

# Add current directory to path
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

def test_basic_functionality():
    """Test basic functionality without external dependencies."""
    print("🧪 Testing Route Optimization System...")
    
    try:
        # Test data loading
        print("\n1. Testing Data Loading...")
        from data_loader import DataLoader
        
        loader = DataLoader()
        trucks = loader.load_trucks("data/trucks.json")
        deliveries = loader.load_delivery_points("data/deliveries.json")
        
        print(f"   ✅ Loaded {len(trucks)} trucks and {len(deliveries)} delivery points")
        
        # Test router (fallback mode)
        print("\n2. Testing Router (Fallback Mode)...")
        from router import Router
        
        router = Router(use_fallback=True)  # Force fallback mode
        route_info = router.get_route_info(trucks[0].start, deliveries[0].location)
        
        print(f"   ✅ Route calculated: {route_info.distance_m:.0f}m, {route_info.duration_s:.0f}s")
        
        # Test matrix calculation
        locations = [truck.start for truck in trucks[:2]] + [deliveries[0].location]
        dist_matrix, time_matrix = router.calculate_distance_matrix(locations)
        
        print(f"   ✅ Matrix calculated: {dist_matrix.shape}")
        
        # Test ETA calculator
        print("\n3. Testing ETA Calculator...")
        from eta_calculator import ETACalculator
        
        eta_calc = ETACalculator(router)
        
        # Create a simple mock route for testing
        from optimizer import OptimizedRoute
        mock_route = OptimizedRoute(
            truck_id=0,
            route=[0, 1],  # First two delivery points
            total_distance_m=5000,
            total_time_s=900,
            total_demand=35
        )
        
        etas = eta_calc.calculate_route_etas(trucks, deliveries, [mock_route])
        print(f"   ✅ ETAs calculated for {len(etas)} trucks")
        
        # Test data summary
        print("\n4. Testing Data Summary...")
        summary = loader.get_summary()
        print(f"   ✅ Summary generated: {summary['trucks']['count']} trucks, {summary['delivery_points']['count']} deliveries")
        
        # Test file operations
        print("\n5. Testing File Operations...")
        test_output = {
            "test_timestamp": datetime.now().isoformat(),
            "trucks_loaded": len(trucks),
            "deliveries_loaded": len(deliveries),
            "sample_route_info": {
                "distance_m": route_info.distance_m,
                "duration_s": route_info.duration_s
            }
        }
        
        with open("output/test_results.json", 'w') as f:
            json.dump(test_output, f, indent=2)
        
        print("   ✅ Test results saved to output/test_results.json")
        
        print("\n✅ Basic functionality test completed successfully!")
        print("\n📝 Notes:")
        print("   - Router is using fallback mode (geodesic distance)")
        print("   - For full functionality, set OPENROUTESERVICE_API_KEY in .env")
        print("   - Install all dependencies: pip install -r requirements.txt")
        
        return True
        
    except Exception as e:
        print(f"\n❌ Test failed: {e}")
        import traceback
        traceback.print_exc()
        return False


def test_with_sample_data():
    """Test with generated sample data."""
    print("\n🧪 Testing with Generated Sample Data...")
    
    try:
        from data_loader import DataLoader
        
        loader = DataLoader()
        trucks, deliveries = loader.generate_sample_data(
            num_trucks=2, num_deliveries=6
        )
        
        print(f"   ✅ Generated {len(trucks)} trucks and {len(deliveries)} delivery points")
        
        # Save sample data
        loader.save_data_to_files("output/sample_trucks.json", "output/sample_deliveries.json")
        print("   ✅ Sample data saved to output/")
        
        return True
        
    except Exception as e:
        print(f"   ❌ Sample data test failed: {e}")
        return False


def test_optimization_pipeline():
    """Test the full optimization pipeline."""
    print("\n🧪 Testing Optimization Pipeline...")
    
    try:
        # Only test if OR-Tools is available
        try:
            from optimizer import RouteOptimizer
        except ImportError:
            print("   ⚠️ OR-Tools not available, skipping optimization test")
            return True
        
        from data_loader import DataLoader
        from router import Router
        
        # Load data
        loader = DataLoader()
        trucks = loader.load_trucks("data/trucks.json")
        deliveries = loader.load_delivery_points("data/deliveries.json")
        
        # Use only subset for faster testing
        trucks = trucks[:2]
        deliveries = deliveries[:6]
        
        # Create components
        router = Router(use_fallback=True)
        optimizer = RouteOptimizer(router)
        
        # Run optimization
        routes = optimizer.optimize_routes(trucks, deliveries)
        
        if routes:
            print(f"   ✅ Optimization successful: {len(routes)} routes generated")
            
            # Save results
            results = {
                "routes": [
                    {
                        "truck_id": r.truck_id,
                        "deliveries": len(r.route),
                        "distance_km": r.total_distance_m / 1000,
                        "time_hours": r.total_time_s / 3600
                    }
                    for r in routes
                ]
            }
            
            with open("output/test_optimization.json", 'w') as f:
                json.dump(results, f, indent=2)
                
            return True
        else:
            print("   ⚠️ No routes generated")
            return False
            
    except ImportError as e:
        print(f"   ⚠️ Dependencies missing: {e}")
        return True  # Don't fail the test for missing optional dependencies
    except Exception as e:
        print(f"   ❌ Optimization test failed: {e}")
        return False


if __name__ == "__main__":
    print("🚚 Route Optimization System - Test Suite")
    print("=" * 50)
    
    success = True
    
    # Run tests
    success &= test_basic_functionality()
    success &= test_with_sample_data()
    success &= test_optimization_pipeline()
    
    print("\n" + "=" * 50)
    if success:
        print("🎉 All tests completed successfully!")
        print("\n🚀 Next steps:")
        print("   1. Get OpenRouteService API key: https://openrouteservice.org/dev/#/signup")
        print("   2. Add API key to .env file")
        print("   3. Install dependencies: pip install -r requirements.txt")
        print("   4. Run: python main.py optimize")
    else:
        print("❌ Some tests failed. Check the output above.")
        sys.exit(1)
