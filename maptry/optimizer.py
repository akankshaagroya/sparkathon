"""
Optimizer module using OR-Tools for multi-vehicle route optimization.
Handles capacity constraints, time windows, and distance/time minimization.
"""

import os
from typing import List, Dict, Tuple, Optional
import numpy as np
from dataclasses import dataclass
from ortools.constraint_solver import routing_enums_pb2
from ortools.constraint_solver import pywrapcp

from data_loader import Truck, DeliveryPoint
from router import Router


@dataclass
class OptimizedRoute:
    """Represents an optimized route for a single truck."""
    truck_id: int
    route: List[int]  # Sequence of delivery point indices
    total_distance_m: float
    total_time_s: float
    total_demand: int


class RouteOptimizer:
    """Optimizes routes for multiple vehicles using OR-Tools."""
    
    def __init__(self, router: Router):
        """
        Initialize optimizer with router for distance calculations.
        
        Args:
            router: Router instance for distance/time calculations
        """
        self.router = router
        self.trucks: List[Truck] = []
        self.delivery_points: List[DeliveryPoint] = []
        self.distance_matrix: Optional[np.ndarray] = None
        self.time_matrix: Optional[np.ndarray] = None
        
        # Optimization parameters
        self.max_search_seconds = int(os.getenv('MAX_SEARCH_SECONDS', 30))
        self.max_route_duration = int(os.getenv('MAX_ROUTE_DURATION_HOURS', 8)) * 3600
    
    def optimize_routes(self, trucks: List[Truck], delivery_points: List[DeliveryPoint],
                       minimize_time: bool = True) -> List[OptimizedRoute]:
        """
        Optimize routes for multiple trucks.
        
        Args:
            trucks: List of available trucks
            delivery_points: List of delivery points to visit
            minimize_time: Whether to minimize time (True) or distance (False)
            
        Returns:
            List of optimized routes for each truck
        """
        self.trucks = trucks
        self.delivery_points = delivery_points
        
        if not trucks or not delivery_points:
            return []
        
        # Prepare data for OR-Tools
        data = self._create_data_model(minimize_time)
        
        # Create routing model
        manager = pywrapcp.RoutingIndexManager(
            len(data['distance_matrix']),
            len(trucks),
            data['depot']
        )
        routing = pywrapcp.RoutingModel(manager)
        
        # Add constraints and objectives
        self._add_distance_constraint(routing, manager, data)
        self._add_capacity_constraint(routing, manager, data)
        self._add_time_window_constraint(routing, manager, data)
        
        # Set search parameters
        search_parameters = pywrapcp.DefaultRoutingSearchParameters()
        search_parameters.first_solution_strategy = (
            routing_enums_pb2.FirstSolutionStrategy.PATH_CHEAPEST_ARC
        )
        search_parameters.local_search_metaheuristic = (
            routing_enums_pb2.LocalSearchMetaheuristic.GUIDED_LOCAL_SEARCH
        )
        search_parameters.time_limit.seconds = self.max_search_seconds
        
        # Solve
        solution = routing.SolveWithParameters(search_parameters)
        
        if solution:
            return self._parse_solution(manager, routing, solution, data)
        else:
            print("No solution found!")
            return []
    
    def _create_data_model(self, minimize_time: bool) -> Dict:
        """Create data model for OR-Tools."""
        # Combine all locations: depot(s) + delivery points
        all_locations = []
        
        # Add truck starting positions as depots
        for truck in self.trucks:
            all_locations.append(truck.start)
        
        # Add delivery point locations
        for point in self.delivery_points:
            all_locations.append(point.location)
        
        # Calculate distance and time matrices
        self.distance_matrix, self.time_matrix = self.router.calculate_distance_matrix(
            all_locations
        )
        
        # Choose optimization metric
        cost_matrix = self.time_matrix if minimize_time else self.distance_matrix
        
        # Create demands array (0 for depots, actual demand for delivery points)
        demands = [0] * len(self.trucks)  # Depots have 0 demand
        demands.extend([point.demand for point in self.delivery_points])
        
        # Create vehicle capacities
        capacities = [truck.capacity for truck in self.trucks]
        
        # Create time windows
        time_windows = []
        
        # Depots: open all day
        for _ in self.trucks:
            time_windows.append((0, 24 * 3600))  # 24 hours in seconds
        
        # Delivery points
        for point in self.delivery_points:
            start_time = self._time_str_to_seconds(point.time_window_start)
            end_time = self._time_str_to_seconds(point.time_window_end)
            time_windows.append((start_time, end_time))
        
        return {
            'distance_matrix': cost_matrix.astype(int),
            'demands': demands,
            'vehicle_capacities': capacities,
            'time_windows': time_windows,
            'depot': 0,  # Use first truck position as main depot
            'num_vehicles': len(self.trucks)
        }
    
    def _add_distance_constraint(self, routing, manager, data):
        """Add distance/time constraint to the model."""
        def distance_callback(from_index, to_index):
            from_node = manager.IndexToNode(from_index)
            to_node = manager.IndexToNode(to_index)
            return data['distance_matrix'][from_node][to_node]
        
        transit_callback_index = routing.RegisterTransitCallback(distance_callback)
        routing.SetArcCostEvaluatorOfAllVehicles(transit_callback_index)
        
        # Add distance dimension
        dimension_name = 'Distance'
        routing.AddDimension(
            transit_callback_index,
            0,  # no slack
            self.max_route_duration,  # maximum route distance/time
            True,  # start cumul to zero
            dimension_name
        )
        distance_dimension = routing.GetDimensionOrDie(dimension_name)
        distance_dimension.SetGlobalSpanCostCoefficient(100)
    
    def _add_capacity_constraint(self, routing, manager, data):
        """Add capacity constraint to the model."""
        def demand_callback(from_index):
            from_node = manager.IndexToNode(from_index)
            return data['demands'][from_node]
        
        demand_callback_index = routing.RegisterUnaryTransitCallback(demand_callback)
        routing.AddDimensionWithVehicleCapacity(
            demand_callback_index,
            0,  # null capacity slack
            data['vehicle_capacities'],  # vehicle maximum capacities
            True,  # start cumul to zero
            'Capacity'
        )
    
    def _add_time_window_constraint(self, routing, manager, data):
        """Add time window constraints."""
        def time_callback(from_index, to_index):
            from_node = manager.IndexToNode(from_index)
            to_node = manager.IndexToNode(to_index)
            # Use time matrix if available, otherwise convert distance to time
            if hasattr(self, 'time_matrix') and self.time_matrix is not None:
                return int(self.time_matrix[from_node][to_node])
            else:
                # Estimate time from distance
                distance = data['distance_matrix'][from_node][to_node]
                avg_speed_ms = 40 * 1000 / 3600  # 40 km/h in m/s
                return int(distance / avg_speed_ms)
        
        time_callback_index = routing.RegisterTransitCallback(time_callback)
        
        routing.AddDimension(
            time_callback_index,
            3600,  # allow waiting time (1 hour)
            24 * 3600,  # maximum time per route (24 hours)
            False,  # don't force start cumul to zero
            'Time'
        )
        
        time_dimension = routing.GetDimensionOrDie('Time')
        
        # Add time window constraints for each location
        for location_idx, time_window in enumerate(data['time_windows']):
            if location_idx < len(self.trucks):
                continue  # Skip depot constraints
            
            index = manager.NodeToIndex(location_idx)
            time_dimension.CumulVar(index).SetRange(time_window[0], time_window[1])
    
    def _parse_solution(self, manager, routing, solution, data) -> List[OptimizedRoute]:
        """Parse OR-Tools solution into OptimizedRoute objects."""
        routes = []
        
        for vehicle_id in range(len(self.trucks)):
            route_indices = []
            total_distance = 0
            total_time = 0
            total_demand = 0
            
            index = routing.Start(vehicle_id)
            
            while not routing.IsEnd(index):
                node_index = manager.IndexToNode(index)
                
                # Skip depot nodes
                if node_index >= len(self.trucks):
                    delivery_point_idx = node_index - len(self.trucks)
                    route_indices.append(delivery_point_idx)
                    total_demand += self.delivery_points[delivery_point_idx].demand
                
                previous_index = index
                index = solution.Value(routing.NextVar(index))
                
                if not routing.IsEnd(index):
                    from_node = manager.IndexToNode(previous_index)
                    to_node = manager.IndexToNode(index)
                    total_distance += self.distance_matrix[from_node][to_node]
                    total_time += self.time_matrix[from_node][to_node]
            
            if route_indices:  # Only include routes with deliveries
                routes.append(OptimizedRoute(
                    truck_id=self.trucks[vehicle_id].id,
                    route=route_indices,
                    total_distance_m=total_distance,
                    total_time_s=total_time,
                    total_demand=total_demand
                ))
        
        return routes
    
    def _time_str_to_seconds(self, time_str: str) -> int:
        """Convert time string (HH:MM) to seconds since midnight."""
        try:
            hours, minutes = map(int, time_str.split(':'))
            return hours * 3600 + minutes * 60
        except:
            return 9 * 3600  # Default to 9 AM
    
    def get_optimization_stats(self, routes: List[OptimizedRoute]) -> Dict:
        """Get optimization statistics."""
        if not routes:
            return {"error": "No routes to analyze"}
        
        total_distance = sum(route.total_distance_m for route in routes)
        total_time = sum(route.total_time_s for route in routes)
        total_demand = sum(route.total_demand for route in routes)
        
        utilized_trucks = len(routes)
        available_trucks = len(self.trucks)
        
        return {
            "optimization_summary": {
                "total_distance_km": total_distance / 1000,
                "total_time_hours": total_time / 3600,
                "total_demand": total_demand,
                "trucks_utilized": utilized_trucks,
                "trucks_available": available_trucks,
                "utilization_rate": f"{(utilized_trucks / available_trucks * 100):.1f}%"
            },
            "routes": [
                {
                    "truck_id": route.truck_id,
                    "deliveries": len(route.route),
                    "distance_km": route.total_distance_m / 1000,
                    "time_hours": route.total_time_s / 3600,
                    "demand": route.total_demand
                }
                for route in routes
            ]
        }


if __name__ == "__main__":
    # Example usage
    from data_loader import DataLoader
    
    # Load sample data
    loader = DataLoader()
    trucks, deliveries = loader.generate_sample_data(num_trucks=2, num_deliveries=8)
    
    # Create router and optimizer
    router = Router()
    optimizer = RouteOptimizer(router)
    
    try:
        # Optimize routes
        routes = optimizer.optimize_routes(trucks, deliveries)
        
        # Print results
        print("Optimization Results:")
        stats = optimizer.get_optimization_stats(routes)
        
        for route in routes:
            print(f"\nTruck {route.truck_id}:")
            print(f"  Deliveries: {len(route.route)}")
            print(f"  Distance: {route.total_distance_m/1000:.1f} km")
            print(f"  Time: {route.total_time_s/3600:.1f} hours")
            print(f"  Demand: {route.total_demand}")
            print(f"  Route: {route.route}")
            
    except Exception as e:
        print(f"Optimization failed: {e}")
