"""
Main orchestration module for the truck route optimizer.
Handles command-line interface, API server, and full pipeline execution.
"""

import os
import sys
import json
import argparse
from datetime import datetime
from typing import List, Dict, Optional

# FastAPI imports
try:
    from fastapi import FastAPI, HTTPException
    from fastapi.responses import HTMLResponse, FileResponse
    from pydantic import BaseModel
    import uvicorn
    FASTAPI_AVAILABLE = True
except ImportError:
    FASTAPI_AVAILABLE = False

# Project imports
from data_loader import DataLoader, Truck, DeliveryPoint
from router import Router

# Optional imports that may not be available
try:
    from optimizer import RouteOptimizer, OptimizedRoute
    OPTIMIZER_AVAILABLE = True
except ImportError:
    print("Warning: OR-Tools not available. Optimization features disabled.")
    OPTIMIZER_AVAILABLE = False

try:
    from eta_calculator import ETACalculator, ETAInfo
    ETA_AVAILABLE = True
except ImportError:
    print("Warning: ETA calculator not available.")
    ETA_AVAILABLE = False

try:
    from reassigner import TruckReassigner
    REASSIGNER_AVAILABLE = True
except ImportError:
    print("Warning: Reassigner not available.")
    REASSIGNER_AVAILABLE = False

try:
    from visualizer import RouteVisualizer
    VISUALIZER_AVAILABLE = True
except ImportError:
    print("Warning: Visualizer not available. Install folium for map features.")
    VISUALIZER_AVAILABLE = False


# Pydantic models for API
if FASTAPI_AVAILABLE:
    class TruckModel(BaseModel):
        id: int
        start: List[float]
        capacity: int = 100
        speed_kmh: float = 40.0

    class DeliveryPointModel(BaseModel):
        id: int
        location: List[float]
        demand: int = 1
        time_window_start: str = "09:00"
        time_window_end: str = "17:00"
        priority: int = 1

    class OptimizeRequest(BaseModel):
        trucks: List[TruckModel]
        delivery_points: List[DeliveryPointModel]
        minimize_time: bool = True
        start_time: str = "09:00"

    class ReassignRequest(BaseModel):
        trucks: List[TruckModel]
        delivery_points: List[DeliveryPointModel]
        current_routes: Dict[int, List[int]]
        failed_truck_id: int
        current_positions: Dict[int, List[float]]


class RouteOptimizerPipeline:
    """Main pipeline for route optimization with all components."""
    
    def __init__(self, api_key: Optional[str] = None):
        """Initialize all components."""
        self.data_loader = DataLoader()
        self.router = Router(api_key=api_key)
        
        # Initialize optional components
        if OPTIMIZER_AVAILABLE:
            self.optimizer = RouteOptimizer(self.router)
        else:
            self.optimizer = None
            
        if ETA_AVAILABLE:
            self.eta_calculator = ETACalculator(self.router)
        else:
            self.eta_calculator = None
            
        if REASSIGNER_AVAILABLE and OPTIMIZER_AVAILABLE and ETA_AVAILABLE:
            self.reassigner = TruckReassigner(self.router, self.optimizer, self.eta_calculator)
        else:
            self.reassigner = None
            
        if VISUALIZER_AVAILABLE:
            self.visualizer = RouteVisualizer(self.router)
        else:
            self.visualizer = None
        
        # Create output directory
        os.makedirs("output", exist_ok=True)
    
    def run_full_optimization(self,
                            trucks_file: str,
                            deliveries_file: str,
                            minimize_time: bool = True,
                            start_time: str = "09:00",
                            output_prefix: str = "output/") -> Dict:
        """
        Run the complete optimization pipeline.
        
        Args:
            trucks_file: Path to trucks JSON file
            deliveries_file: Path to deliveries JSON file
            minimize_time: Whether to minimize time vs distance
            start_time: Start time in HH:MM format
            output_prefix: Output directory prefix
            
        Returns:
            Dictionary with all results
        """
        print("🚚 Starting Route Optimization Pipeline...")
        
        # 1. Load data
        print("📊 Loading data...")
        trucks = self.data_loader.load_trucks(trucks_file)
        delivery_points = self.data_loader.load_delivery_points(deliveries_file)
        
        print(f"   Loaded {len(trucks)} trucks and {len(delivery_points)} delivery points")
        
        # 2. Optimize routes
        print("🔧 Optimizing routes...")
        if not self.optimizer:
            raise Exception("Optimizer not available. Install OR-Tools: pip install ortools")
            
        optimized_routes = self.optimizer.optimize_routes(trucks, delivery_points, minimize_time)
        
        if not optimized_routes:
            raise Exception("No feasible routes found!")
        
        print(f"   Generated {len(optimized_routes)} optimized routes")
        
        # 3. Calculate ETAs
        print("⏰ Calculating ETAs...")
        etas = self.eta_calculator.calculate_route_etas(
            trucks, delivery_points, optimized_routes
        )
        
        # 4. Generate outputs
        print("📁 Generating outputs...")
        
        # Save routes
        routes_output = self._format_routes_output(optimized_routes, delivery_points)
        with open(f"{output_prefix}routes.json", 'w', encoding='utf-8') as f:
            json.dump(routes_output, f, indent=2)
        
        # Save ETAs
        formatted_etas = self._format_etas_output(etas)
        with open(f"{output_prefix}eta_schedule.json", 'w', encoding='utf-8') as f:
            json.dump(formatted_etas, f, indent=2)
        
        # Save summary statistics
        optimization_stats = self.optimizer.get_optimization_stats(optimized_routes)
        eta_summary = self.eta_calculator.get_eta_summary(etas)
        
        summary = {
            "optimization": optimization_stats,
            "eta_summary": eta_summary,
            "generation_timestamp": datetime.now().isoformat(),
            "parameters": {
                "minimize_time": minimize_time,
                "start_time": start_time,
                "trucks_count": len(trucks),
                "delivery_points_count": len(delivery_points)
            }
        }
        
        with open(f"{output_prefix}summary.json", 'w', encoding='utf-8') as f:
            json.dump(summary, f, indent=2)
        
        # 5. Create visualizations
        print("🗺️ Creating visualizations...")
        
        try:
            # Interactive map
            route_map = self.visualizer.create_route_map(
                trucks, delivery_points, optimized_routes, etas
            )
            self.visualizer.save_map(route_map, f"{output_prefix}route_map.html")
            
            # HTML summary
            summary_html = self.visualizer.generate_route_summary_html(
                trucks, delivery_points, optimized_routes, etas
            )
            with open(f"{output_prefix}route_summary.html", 'w', encoding='utf-8') as f:
                f.write(summary_html)
                
        except Exception as e:
            print(f"Warning: Visualization failed: {e}")
        
        print("✅ Pipeline complete!")
        print(f"📁 Results saved to: {output_prefix}")
        
        return {
            "routes": routes_output,
            "etas": formatted_etas,
            "summary": summary,
            "optimization_stats": optimization_stats
        }
    
    def _format_etas_output(self, etas: Dict[str, List[ETAInfo]]) -> Dict:
        """Convert ETAInfo objects to dictionary format for JSON serialization."""
        formatted_etas = {}
        
        for truck_id, eta_list in etas.items():
            formatted_etas[truck_id] = []
            
            for eta_info in eta_list:
                formatted_etas[truck_id].append({
                    "point_id": eta_info.point_id,
                    "coordinates": eta_info.coordinates,
                    "eta": eta_info.eta,
                    "distance_from_previous_m": eta_info.distance_from_previous_m,
                    "travel_time_minutes": eta_info.travel_time_minutes,
                    "arrival_time_seconds": eta_info.arrival_time_seconds
                })
        
        return formatted_etas

    def _format_routes_output(self, optimized_routes: List[OptimizedRoute], 
                            delivery_points: List[DeliveryPoint]) -> Dict:
        """Format routes for JSON output."""
        output = {}
        
        for route in optimized_routes:
            route_info = []
            
            for point_idx in route.route:
                if point_idx < len(delivery_points):
                    point = delivery_points[point_idx]
                    route_info.append({
                        "point_id": point.id,
                        "coordinates": point.location,
                        "demand": point.demand,
                        "time_window": f"{point.time_window_start}-{point.time_window_end}",
                        "priority": point.priority
                    })
            
            output[str(route.truck_id)] = {
                "deliveries": route_info,
                "total_distance_km": route.total_distance_m / 1000,
                "total_time_hours": route.total_time_s / 3600,
                "total_demand": route.total_demand
            }
        
        return output
    
    def simulate_failure_scenario(self,
                                trucks_file: str,
                                deliveries_file: str,
                                failed_truck_id: int,
                                output_prefix: str = "output/failure_") -> Dict:
        """Simulate truck failure and reassignment."""
        print(f"🚨 Simulating failure of truck {failed_truck_id}...")
        
        # Load data and run initial optimization
        trucks = self.data_loader.load_trucks(trucks_file)
        delivery_points = self.data_loader.load_delivery_points(deliveries_file)
        initial_routes = self.optimizer.optimize_routes(trucks, delivery_points)
        
        # Simulate failure
        reassignment_result = self.reassigner.simulate_truck_breakdown(
            trucks, delivery_points, initial_routes, failed_truck_id
        )
        
        # Save reassignment results
        with open(f"{output_prefix}reassignment.json", 'w', encoding='utf-8') as f:
            json.dump({
                "reassigned_points": reassignment_result.reassigned_points,
                "updated_routes": reassignment_result.updated_routes,
                "summary": reassignment_result.reassignment_summary
            }, f, indent=2)
        
        # Save updated ETAs
        formatted_updated_etas = self._format_etas_output(reassignment_result.updated_etas)
        with open(f"{output_prefix}updated_etas.json", 'w', encoding='utf-8') as f:
            json.dump(formatted_updated_etas, f, indent=2)
        
        # Create comparison visualization
        try:
            comparison_map = self.visualizer.create_comparison_map(
                trucks, delivery_points, initial_routes,
                reassignment_result.updated_routes, failed_truck_id
            )
            self.visualizer.save_map(comparison_map, f"{output_prefix}comparison_map.html")
        except Exception as e:
            print(f"Warning: Comparison visualization failed: {e}")
        
        return {
            "initial_routes": [
                {"truck_id": r.truck_id, "route": r.route} for r in initial_routes
            ],
            "reassignment_result": {
                "reassigned_points": reassignment_result.reassigned_points,
                "updated_routes": reassignment_result.updated_routes,
                "updated_etas": formatted_updated_etas,
                "summary": reassignment_result.reassignment_summary
            }
        }


# FastAPI app setup
if FASTAPI_AVAILABLE:
    app = FastAPI(title="Truck Route Optimizer API", version="1.0.0")
    pipeline = RouteOptimizerPipeline()

    @app.get("/")
    async def root():
        return {"message": "Truck Route Optimizer API", "version": "1.0.0"}

    @app.get("/health")
    async def health_check():
        return {"status": "healthy", "timestamp": datetime.now().isoformat()}

    @app.post("/optimize")
    async def optimize_routes(request: OptimizeRequest):
        try:
            # Convert Pydantic models to domain objects
            trucks = [
                Truck(id=t.id, start=t.start, capacity=t.capacity, speed_kmh=t.speed_kmh)
                for t in request.trucks
            ]
            
            delivery_points = [
                DeliveryPoint(
                    id=p.id, location=p.location, demand=p.demand,
                    time_window_start=p.time_window_start,
                    time_window_end=p.time_window_end,
                    priority=p.priority
                )
                for p in request.delivery_points
            ]
            
            # Optimize routes
            optimized_routes = pipeline.optimizer.optimize_routes(
                trucks, delivery_points, request.minimize_time
            )
            
            # Calculate ETAs
            etas = pipeline.eta_calculator.calculate_route_etas(
                trucks, delivery_points, optimized_routes
            )
            
            return {
                "routes": pipeline._format_routes_output(optimized_routes, delivery_points),
                "etas": etas,
                "summary": pipeline.optimizer.get_optimization_stats(optimized_routes)
            }
            
        except Exception as e:
            raise HTTPException(status_code=500, detail=str(e))

    @app.post("/reassign")
    async def reassign_routes(request: ReassignRequest):
        try:
            # Convert to domain objects
            trucks = [
                Truck(id=t.id, start=t.start, capacity=t.capacity, speed_kmh=t.speed_kmh)
                for t in request.trucks
            ]
            
            delivery_points = [
                DeliveryPoint(
                    id=p.id, location=p.location, demand=p.demand,
                    time_window_start=p.time_window_start,
                    time_window_end=p.time_window_end,
                    priority=p.priority
                )
                for p in request.delivery_points
            ]
            
            # Handle reassignment
            result = pipeline.reassigner.handle_truck_failure(
                trucks, delivery_points, request.current_routes,
                request.failed_truck_id, request.current_positions
            )
            
            return {
                "reassigned_points": result.reassigned_points,
                "updated_routes": result.updated_routes,
                "updated_etas": result.updated_etas,
                "summary": result.reassignment_summary
            }
            
        except Exception as e:
            raise HTTPException(status_code=500, detail=str(e))

    @app.get("/visualize/{filename}")
    async def get_visualization(filename: str):
        file_path = f"output/{filename}"
        if os.path.exists(file_path):
            return FileResponse(file_path)
        else:
            raise HTTPException(status_code=404, detail="Visualization not found")


def main():
    """Main entry point with command-line interface."""
    parser = argparse.ArgumentParser(description="Truck Route Optimizer")
    
    # Subcommands
    subparsers = parser.add_subparsers(dest='command', help='Available commands')
    
    # Optimize command
    optimize_parser = subparsers.add_parser('optimize', help='Run route optimization')
    optimize_parser.add_argument('--trucks', default='data/trucks.json', 
                               help='Trucks JSON file')
    optimize_parser.add_argument('--deliveries', default='data/deliveries.json',
                               help='Deliveries JSON file')
    optimize_parser.add_argument('--minimize-distance', action='store_true',
                               help='Minimize distance instead of time')
    optimize_parser.add_argument('--start-time', default='09:00',
                               help='Start time (HH:MM)')
    optimize_parser.add_argument('--output', default='output/',
                               help='Output directory')
    
    # Generate sample data command
    sample_parser = subparsers.add_parser('generate-sample', help='Generate sample data')
    sample_parser.add_argument('--trucks', type=int, default=3,
                             help='Number of trucks')
    sample_parser.add_argument('--deliveries', type=int, default=15,
                             help='Number of delivery points')
    sample_parser.add_argument('--center-lat', type=float, default=19.0760,
                             help='Center latitude')
    sample_parser.add_argument('--center-lon', type=float, default=72.8777,
                             help='Center longitude')
    sample_parser.add_argument('--radius', type=float, default=20,
                             help='Radius in km')
    
    # Simulate failure command
    failure_parser = subparsers.add_parser('simulate-failure', 
                                         help='Simulate truck failure')
    failure_parser.add_argument('--trucks', default='data/trucks.json',
                              help='Trucks JSON file')
    failure_parser.add_argument('--deliveries', default='data/deliveries.json',
                              help='Deliveries JSON file')
    failure_parser.add_argument('--failed-truck', type=int, required=True,
                              help='ID of truck to fail')
    failure_parser.add_argument('--output', default='output/failure_',
                              help='Output prefix')
    
    # API server command
    if FASTAPI_AVAILABLE:
        api_parser = subparsers.add_parser('api', help='Start API server')
        api_parser.add_argument('--host', default='127.0.0.1', help='Host address')
        api_parser.add_argument('--port', type=int, default=8000, help='Port number')
        api_parser.add_argument('--reload', action='store_true', help='Enable auto-reload')
    
    args = parser.parse_args()
    
    if not args.command:
        parser.print_help()
        return
    
    try:
        pipeline = RouteOptimizerPipeline()
        
        if args.command == 'generate-sample':
            print("🔧 Generating sample data...")
            trucks, deliveries = pipeline.data_loader.generate_sample_data(
                args.trucks, args.deliveries, args.center_lat, args.center_lon, args.radius
            )
            
            os.makedirs("data", exist_ok=True)
            pipeline.data_loader.save_data_to_files(
                "data/trucks.json", "data/deliveries.json"
            )
            
            print(f"✅ Generated {len(trucks)} trucks and {len(deliveries)} delivery points")
            print("📁 Saved to data/trucks.json and data/deliveries.json")
            
        elif args.command == 'optimize':
            result = pipeline.run_full_optimization(
                args.trucks, args.deliveries, 
                minimize_time=not args.minimize_distance,
                start_time=args.start_time,
                output_prefix=args.output
            )
            
        elif args.command == 'simulate-failure':
            result = pipeline.simulate_failure_scenario(
                args.trucks, args.deliveries, args.failed_truck, args.output
            )
            print(f"✅ Failure simulation complete! Results in {args.output}*")
            
        elif args.command == 'api' and FASTAPI_AVAILABLE:
            print(f"🚀 Starting API server on {args.host}:{args.port}")
            print(f"📖 API docs available at: http://{args.host}:{args.port}/docs")
            uvicorn.run("main:app", host=args.host, port=args.port, reload=args.reload)
            
        else:
            print(f"Unknown command: {args.command}")
            parser.print_help()
            
    except Exception as e:
        print(f"❌ Error: {e}")
        sys.exit(1)


if __name__ == "__main__":
    main()
