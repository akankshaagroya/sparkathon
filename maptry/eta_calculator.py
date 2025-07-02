"""
ETA Calculator module for computing estimated times of arrival.
Calculates ETAs based on route optimization and real travel times.
"""

from typing import List, Dict, Optional
from datetime import datetime, timedelta
from dataclasses import dataclass
import json

from data_loader import Truck, DeliveryPoint
from optimizer import OptimizedRoute
from router import Router


@dataclass
class ETAInfo:
    """Contains ETA information for a delivery point."""
    point_id: int
    coordinates: List[float]
    eta: str  # ISO format datetime string
    distance_from_previous_m: float
    travel_time_minutes: float
    arrival_time_seconds: int  # Seconds since start of day


class ETACalculator:
    """Calculates estimated times of arrival for optimized routes."""
    
    def __init__(self, router: Router, start_time: str = "09:00"):
        """
        Initialize ETA calculator.
        
        Args:
            router: Router instance for distance/time calculations
            start_time: Start time in HH:MM format
        """
        self.router = router
        self.start_time = start_time
        self.start_datetime = self._parse_start_time(start_time)
        
        # Service time per delivery (in seconds)
        self.service_time_per_delivery = 300  # 5 minutes default
        
        # Break time settings
        self.break_duration = 1800  # 30 minutes
        self.break_interval = 4 * 3600  # Every 4 hours
    
    def calculate_route_etas(self, 
                           trucks: List[Truck],
                           delivery_points: List[DeliveryPoint],
                           optimized_routes: List[OptimizedRoute],
                           start_date: Optional[str] = None) -> Dict[str, List[ETAInfo]]:
        """
        Calculate ETAs for all routes.
        
        Args:
            trucks: List of truck objects
            delivery_points: List of delivery point objects  
            optimized_routes: List of optimized routes
            start_date: Date in YYYY-MM-DD format (defaults to today)
            
        Returns:
            Dictionary mapping truck_id to list of ETA info
        """
        if start_date is None:
            start_date = datetime.now().strftime("%Y-%m-%d")
        
        # Create lookup dictionaries
        truck_dict = {truck.id: truck for truck in trucks}
        point_dict = {point.id: point for point in delivery_points}
        
        all_etas = {}
        
        for route in optimized_routes:
            truck = truck_dict[route.truck_id]
            
            etas = self._calculate_single_route_eta(
                truck, delivery_points, route, start_date
            )
            
            all_etas[str(route.truck_id)] = etas
        
        return all_etas
    
    def _calculate_single_route_eta(self,
                                  truck: Truck,
                                  delivery_points: List[DeliveryPoint],
                                  route: OptimizedRoute,
                                  start_date: str) -> List[ETAInfo]:
        """Calculate ETAs for a single route."""
        etas = []
        
        # Start from truck's starting position
        current_position = truck.start
        current_time = self._parse_datetime(start_date, self.start_time)
        
        total_travel_time = 0
        
        for i, point_idx in enumerate(route.route):
            delivery_point = delivery_points[point_idx]
            
            # Calculate travel to this point
            route_info = self.router.get_route_info(
                current_position, 
                delivery_point.location
            )
            
            # Add travel time
            travel_time_seconds = route_info.duration_s
            current_time += timedelta(seconds=travel_time_seconds)
            total_travel_time += travel_time_seconds
            
            # Check if break is needed
            if total_travel_time > self.break_interval and i > 0:
                current_time += timedelta(seconds=self.break_duration)
                total_travel_time = 0  # Reset break timer
            
            # Check time window constraints
            current_time = self._enforce_time_window(
                current_time, delivery_point, start_date
            )
            
            # Create ETA info
            eta_info = ETAInfo(
                point_id=delivery_point.id,
                coordinates=delivery_point.location,
                eta=current_time.isoformat() + "Z",
                distance_from_previous_m=route_info.distance_m,
                travel_time_minutes=travel_time_seconds / 60,
                arrival_time_seconds=self._time_to_seconds_since_midnight(current_time)
            )
            
            etas.append(eta_info)
            
            # Add service time
            current_time += timedelta(seconds=self.service_time_per_delivery)
            
            # Update current position
            current_position = delivery_point.location
        
        return etas
    
    def _enforce_time_window(self, 
                           arrival_time: datetime, 
                           delivery_point: DeliveryPoint,
                           start_date: str) -> datetime:
        """Ensure arrival time is within delivery point's time window."""
        # Parse time window
        window_start = self._parse_datetime(start_date, delivery_point.time_window_start)
        window_end = self._parse_datetime(start_date, delivery_point.time_window_end)
        
        # If arriving too early, wait until window opens
        if arrival_time < window_start:
            return window_start
        
        # If arriving too late, flag as late (but still return the time)
        if arrival_time > window_end:
            print(f"Warning: Late arrival at point {delivery_point.id}")
        
        return arrival_time
    
    def _parse_start_time(self, time_str: str) -> datetime:
        """Parse start time string into datetime object."""
        today = datetime.now().date()
        time_obj = datetime.strptime(time_str, "%H:%M").time()
        return datetime.combine(today, time_obj)
    
    def _parse_datetime(self, date_str: str, time_str: str) -> datetime:
        """Parse date and time strings into datetime object."""
        date_obj = datetime.strptime(date_str, "%Y-%m-%d").date()
        time_obj = datetime.strptime(time_str, "%H:%M").time()
        return datetime.combine(date_obj, time_obj)
    
    def _time_to_seconds_since_midnight(self, dt: datetime) -> int:
        """Convert datetime to seconds since midnight."""
        midnight = datetime.combine(dt.date(), datetime.min.time())
        delta = dt - midnight
        return int(delta.total_seconds())
    
    def update_etas_after_reassignment(self,
                                     truck: Truck,
                                     delivery_points: List[DeliveryPoint],
                                     new_route_indices: List[int],
                                     current_time: datetime,
                                     current_position: List[float]) -> List[ETAInfo]:
        """
        Update ETAs after route reassignment.
        
        Args:
            truck: Truck object
            delivery_points: List of all delivery points
            new_route_indices: New route as list of delivery point indices
            current_time: Current time when reassignment happens
            current_position: Current position [lat, lon]
            
        Returns:
            Updated list of ETA info
        """
        etas = []
        
        # Start from current position and time
        position = current_position
        time = current_time
        
        for point_idx in new_route_indices:
            delivery_point = delivery_points[point_idx]
            
            # Calculate travel to this point
            route_info = self.router.get_route_info(position, delivery_point.location)
            
            # Add travel time
            time += timedelta(seconds=route_info.duration_s)
            
            # Enforce time window
            start_date = time.strftime("%Y-%m-%d")
            time = self._enforce_time_window(time, delivery_point, start_date)
            
            # Create ETA info
            eta_info = ETAInfo(
                point_id=delivery_point.id,
                coordinates=delivery_point.location,
                eta=time.isoformat() + "Z",
                distance_from_previous_m=route_info.distance_m,
                travel_time_minutes=route_info.duration_s / 60,
                arrival_time_seconds=self._time_to_seconds_since_midnight(time)
            )
            
            etas.append(eta_info)
            
            # Add service time and update position
            time += timedelta(seconds=self.service_time_per_delivery)
            position = delivery_point.location
        
        return etas
    
    def get_eta_summary(self, etas: Dict[str, List[ETAInfo]]) -> Dict:
        """Get summary statistics for ETAs."""
        total_deliveries = sum(len(truck_etas) for truck_etas in etas.values())
        total_distance = sum(
            sum(eta.distance_from_previous_m for eta in truck_etas)
            for truck_etas in etas.values()
        )
        total_travel_time = sum(
            sum(eta.travel_time_minutes for eta in truck_etas)
            for truck_etas in etas.values()
        )
        
        # Find earliest and latest deliveries
        all_etas = [eta for truck_etas in etas.values() for eta in truck_etas]
        
        if all_etas:
            earliest = min(all_etas, key=lambda x: x.arrival_time_seconds)
            latest = max(all_etas, key=lambda x: x.arrival_time_seconds)
            
            earliest_time = datetime.fromisoformat(earliest.eta.rstrip('Z'))
            latest_time = datetime.fromisoformat(latest.eta.rstrip('Z'))
            
            return {
                "summary": {
                    "total_deliveries": total_deliveries,
                    "total_distance_km": total_distance / 1000,
                    "total_travel_time_hours": total_travel_time / 60,
                    "earliest_delivery": earliest.eta,
                    "latest_delivery": latest.eta,
                    "delivery_window_hours": (latest_time - earliest_time).total_seconds() / 3600
                },
                "trucks": {
                    truck_id: {
                        "deliveries": len(truck_etas),
                        "distance_km": sum(eta.distance_from_previous_m for eta in truck_etas) / 1000,
                        "travel_time_hours": sum(eta.travel_time_minutes for eta in truck_etas) / 60,
                        "first_delivery": truck_etas[0].eta if truck_etas else None,
                        "last_delivery": truck_etas[-1].eta if truck_etas else None
                    }
                    for truck_id, truck_etas in etas.items()
                }
            }
        
        return {"error": "No ETAs to summarize"}
    
    def export_etas_to_json(self, etas: Dict[str, List[ETAInfo]], 
                           filename: str) -> None:
        """Export ETAs to JSON file."""
        # Convert to serializable format
        export_data = {}
        
        for truck_id, truck_etas in etas.items():
            export_data[truck_id] = [
                {
                    "point_id": eta.point_id,
                    "coordinates": eta.coordinates,
                    "eta": eta.eta,
                    "distance_from_previous_m": eta.distance_from_previous_m,
                    "travel_time_minutes": eta.travel_time_minutes
                }
                for eta in truck_etas
            ]
        
        with open(filename, 'w', encoding='utf-8') as f:
            json.dump(export_data, f, indent=2)


if __name__ == "__main__":
    # Example usage
    from data_loader import DataLoader
    from optimizer import RouteOptimizer
    
    # Generate sample data
    loader = DataLoader()
    trucks, deliveries = loader.generate_sample_data(num_trucks=2, num_deliveries=6)
    
    # Create components
    router = Router()
    optimizer = RouteOptimizer(router)
    eta_calculator = ETACalculator(router)
    
    try:
        # Optimize routes
        routes = optimizer.optimize_routes(trucks, deliveries)
        
        # Calculate ETAs
        etas = eta_calculator.calculate_route_etas(trucks, deliveries, routes)
        
        # Print results
        print("ETA Calculation Results:")
        summary = eta_calculator.get_eta_summary(etas)
        print(json.dumps(summary, indent=2))
        
    except Exception as e:
        print(f"ETA calculation failed: {e}")
