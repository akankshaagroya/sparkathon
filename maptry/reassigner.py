"""
Reassigner module for handling truck failures and dynamic route reassignment.
Identifies unvisited delivery points and reassigns them to closest available trucks.
"""

from typing import List, Dict, Tuple, Optional
import json
from datetime import datetime
from dataclasses import dataclass

from data_loader import Truck, DeliveryPoint
from optimizer import OptimizedRoute, RouteOptimizer
from eta_calculator import ETACalculator, ETAInfo
from router import Router


@dataclass
class ReassignmentResult:
    """Result of a reassignment operation."""
    reassigned_points: List[int]  # Delivery point IDs that were reassigned
    updated_routes: Dict[int, List[int]]  # Updated routes for affected trucks
    updated_etas: Dict[str, List[ETAInfo]]  # Updated ETAs
    reassignment_summary: Dict


class TruckReassigner:
    """Handles dynamic reassignment when trucks fail or become unavailable."""
    
    def __init__(self, router: Router, optimizer: RouteOptimizer, eta_calculator: ETACalculator):
        """
        Initialize reassigner with required components.
        
        Args:
            router: Router instance for distance calculations
            optimizer: Route optimizer for reoptimization
            eta_calculator: ETA calculator for updated schedules
        """
        self.router = router
        self.optimizer = optimizer
        self.eta_calculator = eta_calculator
    
    def handle_truck_failure(self,
                           trucks: List[Truck],
                           delivery_points: List[DeliveryPoint],
                           current_routes: Dict[int, List[int]],
                           failed_truck_id: int,
                           current_positions: Dict[int, List[float]],
                           current_time: Optional[datetime] = None) -> ReassignmentResult:
        """
        Handle truck failure by reassigning unvisited delivery points.
        
        Args:
            trucks: List of all trucks
            delivery_points: List of all delivery points
            current_routes: Current routes as dict {truck_id: [point_indices]}
            failed_truck_id: ID of the failed truck
            current_positions: Current positions as {truck_id: [lat, lon]}
            current_time: Current time (defaults to now)
            
        Returns:
            ReassignmentResult with updated routes and ETAs
        """
        if current_time is None:
            current_time = datetime.now()
        
        # Identify unvisited delivery points from failed truck
        failed_route = current_routes.get(failed_truck_id, [])
        unvisited_points = self._find_unvisited_points(
            failed_truck_id, failed_route, current_positions, delivery_points
        )
        
        if not unvisited_points:
            return ReassignmentResult(
                reassigned_points=[],
                updated_routes={},
                updated_etas={},
                reassignment_summary={"message": "No points to reassign"}
            )
        
        # Find best reassignment for each unvisited point
        reassignments = self._find_optimal_reassignments(
            unvisited_points, trucks, delivery_points, 
            current_routes, current_positions, failed_truck_id
        )
        
        # Update routes
        updated_routes = current_routes.copy()
        del updated_routes[failed_truck_id]  # Remove failed truck
        
        for truck_id, new_points in reassignments.items():
            if truck_id in updated_routes:
                updated_routes[truck_id].extend(new_points)
            else:
                updated_routes[truck_id] = new_points
        
        # Reoptimize affected routes
        updated_routes = self._reoptimize_affected_routes(
            trucks, delivery_points, updated_routes, current_positions
        )
        
        # Calculate updated ETAs
        updated_etas = self._calculate_updated_etas(
            trucks, delivery_points, updated_routes, 
            current_positions, current_time
        )
        
        # Create summary
        summary = self._create_reassignment_summary(
            unvisited_points, reassignments, current_time
        )
        
        return ReassignmentResult(
            reassigned_points=[point.id for point in unvisited_points],
            updated_routes=updated_routes,
            updated_etas=updated_etas,
            reassignment_summary=summary
        )
    
    def _find_unvisited_points(self,
                             failed_truck_id: int,
                             failed_route: List[int],
                             current_positions: Dict[int, List[float]],
                             delivery_points: List[DeliveryPoint]) -> List[DeliveryPoint]:
        """Find delivery points that haven't been visited by the failed truck."""
        # For simplicity, assume truck hasn't started or is at the beginning
        # In a real implementation, you'd track actual progress
        
        failed_truck_position = current_positions.get(failed_truck_id, [0, 0])
        
        # Assume all points in the route are unvisited
        # In practice, you'd track which points have been completed
        unvisited_points = []
        
        for point_idx in failed_route:
            if point_idx < len(delivery_points):
                unvisited_points.append(delivery_points[point_idx])
        
        return unvisited_points
    
    def _find_optimal_reassignments(self,
                                  unvisited_points: List[DeliveryPoint],
                                  trucks: List[Truck],
                                  delivery_points: List[DeliveryPoint],
                                  current_routes: Dict[int, List[int]],
                                  current_positions: Dict[int, List[float]],
                                  failed_truck_id: int) -> Dict[int, List[int]]:
        """Find optimal reassignment of points to available trucks."""
        reassignments = {}
        
        # Get available trucks (excluding failed one)
        available_trucks = [t for t in trucks if t.id != failed_truck_id]
        
        if not available_trucks:
            return reassignments
        
        # Create point index mapping
        point_id_to_idx = {point.id: idx for idx, point in enumerate(delivery_points)}
        
        for point in unvisited_points:
            best_truck_id = None
            best_distance = float('inf')
            
            # Find closest available truck
            for truck in available_trucks:
                truck_position = current_positions.get(truck.id, truck.start)
                
                # Calculate distance from truck's current position to the delivery point
                route_info = self.router.get_route_info(truck_position, point.location)
                distance = route_info.distance_m
                
                # Consider truck capacity
                current_load = self._calculate_current_load(
                    truck.id, current_routes, delivery_points
                )
                
                if current_load + point.demand <= truck.capacity and distance < best_distance:
                    best_distance = distance
                    best_truck_id = truck.id
            
            # Assign to best truck
            if best_truck_id is not None:
                point_idx = point_id_to_idx[point.id]
                if best_truck_id not in reassignments:
                    reassignments[best_truck_id] = []
                reassignments[best_truck_id].append(point_idx)
        
        return reassignments
    
    def _calculate_current_load(self,
                              truck_id: int,
                              current_routes: Dict[int, List[int]],
                              delivery_points: List[DeliveryPoint]) -> int:
        """Calculate current load for a truck."""
        route = current_routes.get(truck_id, [])
        total_demand = 0
        
        for point_idx in route:
            if point_idx < len(delivery_points):
                total_demand += delivery_points[point_idx].demand
        
        return total_demand
    
    def _reoptimize_affected_routes(self,
                                  trucks: List[Truck],
                                  delivery_points: List[DeliveryPoint],
                                  updated_routes: Dict[int, List[int]],
                                  current_positions: Dict[int, List[float]]) -> Dict[int, List[int]]:
        """Reoptimize routes for trucks that received new delivery points."""
        optimized_routes = {}
        
        for truck_id, route_indices in updated_routes.items():
            if not route_indices:
                continue
            
            # Get truck object
            truck = next((t for t in trucks if t.id == truck_id), None)
            if not truck:
                continue
            
            # Update truck's current position
            truck.current_position = current_positions.get(truck_id, truck.start)
            
            # Get delivery points for this route
            route_points = [delivery_points[idx] for idx in route_indices 
                          if idx < len(delivery_points)]
            
            if len(route_points) <= 1:
                optimized_routes[truck_id] = route_indices
                continue
            
            # Simple reordering based on distance (for single truck optimization)
            optimized_order = self._optimize_single_route(
                truck, route_points, delivery_points
            )
            
            optimized_routes[truck_id] = optimized_order
        
        return optimized_routes
    
    def _optimize_single_route(self,
                             truck: Truck,
                             route_points: List[DeliveryPoint],
                             all_delivery_points: List[DeliveryPoint]) -> List[int]:
        """Optimize order of delivery points for a single truck using nearest neighbor."""
        if len(route_points) <= 1:
            # Find indices of these points in the main list
            return [all_delivery_points.index(p) for p in route_points]
        
        # Nearest neighbor heuristic
        unvisited = route_points.copy()
        current_position = truck.current_position
        ordered_route = []
        
        while unvisited:
            # Find nearest unvisited point
            nearest_point = None
            nearest_distance = float('inf')
            
            for point in unvisited:
                distance = self.router.get_route_info(current_position, point.location).distance_m
                if distance < nearest_distance:
                    nearest_distance = distance
                    nearest_point = point
            
            # Add to route and update position
            if nearest_point:
                ordered_route.append(nearest_point)
                current_position = nearest_point.location
                unvisited.remove(nearest_point)
        
        # Convert back to indices
        return [all_delivery_points.index(p) for p in ordered_route]
    
    def _calculate_updated_etas(self,
                              trucks: List[Truck],
                              delivery_points: List[DeliveryPoint],
                              updated_routes: Dict[int, List[int]],
                              current_positions: Dict[int, List[float]],
                              current_time: datetime) -> Dict[str, List[ETAInfo]]:
        """Calculate updated ETAs for all affected routes."""
        updated_etas = {}
        
        for truck_id, route_indices in updated_routes.items():
            if not route_indices:
                continue
            
            # Get truck object
            truck = next((t for t in trucks if t.id == truck_id), None)
            if not truck:
                continue
            
            # Update truck's current position
            truck_position = current_positions.get(truck_id, truck.start)
            
            # Calculate ETAs for this route
            etas = self.eta_calculator.update_etas_after_reassignment(
                truck, delivery_points, route_indices, current_time, truck_position
            )
            
            updated_etas[str(truck_id)] = etas
        
        return updated_etas
    
    def _create_reassignment_summary(self,
                                   unvisited_points: List[DeliveryPoint],
                                   reassignments: Dict[int, List[int]],
                                   current_time: datetime) -> Dict:
        """Create summary of reassignment operation."""
        return {
            "timestamp": current_time.isoformat(),
            "unvisited_points_count": len(unvisited_points),
            "unvisited_point_ids": [p.id for p in unvisited_points],
            "affected_trucks": list(reassignments.keys()),
            "reassignment_details": {
                str(truck_id): {
                    "new_deliveries_count": len(point_indices),
                    "new_delivery_indices": point_indices
                }
                for truck_id, point_indices in reassignments.items()
            },
            "total_reassigned_deliveries": sum(len(points) for points in reassignments.values())
        }
    
    def simulate_truck_breakdown(self,
                               trucks: List[Truck],
                               delivery_points: List[DeliveryPoint],
                               optimized_routes: List[OptimizedRoute],
                               breakdown_truck_id: int,
                               breakdown_after_deliveries: int = 0) -> ReassignmentResult:
        """
        Simulate a truck breakdown scenario for testing.
        
        Args:
            trucks: List of all trucks
            delivery_points: List of all delivery points
            optimized_routes: Original optimized routes
            breakdown_truck_id: ID of truck that breaks down
            breakdown_after_deliveries: Number of deliveries completed before breakdown
            
        Returns:
            ReassignmentResult
        """
        # Convert optimized routes to current routes format
        current_routes = {}
        for route in optimized_routes:
            current_routes[route.truck_id] = route.route
        
        # Simulate partial completion
        if breakdown_truck_id in current_routes:
            original_route = current_routes[breakdown_truck_id]
            remaining_route = original_route[breakdown_after_deliveries:]
            current_routes[breakdown_truck_id] = remaining_route
        
        # Simulate current positions (trucks at their start positions)
        current_positions = {truck.id: truck.start for truck in trucks}
        
        # If some deliveries were completed, update position
        if (breakdown_truck_id in current_routes and 
            breakdown_after_deliveries > 0 and 
            breakdown_after_deliveries <= len(current_routes[breakdown_truck_id])):
            
            completed_deliveries = current_routes[breakdown_truck_id][:breakdown_after_deliveries]
            if completed_deliveries:
                last_delivery_idx = completed_deliveries[-1]
                if last_delivery_idx < len(delivery_points):
                    current_positions[breakdown_truck_id] = delivery_points[last_delivery_idx].location
        
        return self.handle_truck_failure(
            trucks, delivery_points, current_routes,
            breakdown_truck_id, current_positions
        )


if __name__ == "__main__":
    # Example usage and testing
    from data_loader import DataLoader
    
    # Generate sample data
    loader = DataLoader()
    trucks, deliveries = loader.generate_sample_data(num_trucks=3, num_deliveries=12)
    
    # Create components
    router = Router()
    optimizer = RouteOptimizer(router)
    eta_calculator = ETACalculator(router)
    reassigner = TruckReassigner(router, optimizer, eta_calculator)
    
    try:
        # Initial optimization
        routes = optimizer.optimize_routes(trucks, deliveries)
        print("Initial Routes:")
        for route in routes:
            print(f"Truck {route.truck_id}: {len(route.route)} deliveries")
        
        # Simulate truck breakdown
        if routes:
            breakdown_truck = routes[0].truck_id
            print(f"\nSimulating breakdown of truck {breakdown_truck}")
            
            result = reassigner.simulate_truck_breakdown(
                trucks, deliveries, routes, breakdown_truck, 0
            )
            
            print("Reassignment Summary:")
            print(json.dumps(result.reassignment_summary, indent=2))
            
            print(f"\nReassigned {len(result.reassigned_points)} delivery points")
            print(f"Updated routes for {len(result.updated_routes)} trucks")
        
    except Exception as e:
        print(f"Reassignment test failed: {e}")
