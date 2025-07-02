"""
Data loader module for truck route optimizer.
Handles loading and validation of truck and delivery point data.
"""

import json
from typing import List, Dict, Any, Optional
from dataclasses import dataclass
from datetime import datetime
import os


@dataclass
class Truck:
    """Represents a delivery truck with its properties."""
    id: int
    start: List[float]  # [lat, lon]
    capacity: int = 100
    speed_kmh: float = 40.0
    current_position: Optional[List[float]] = None
    
    def __post_init__(self):
        if self.current_position is None:
            self.current_position = self.start.copy()


@dataclass
class DeliveryPoint:
    """Represents a delivery point with its properties."""
    id: int
    location: List[float]  # [lat, lon]
    demand: int = 1
    time_window_start: str = "09:00"
    time_window_end: str = "17:00"
    priority: int = 1  # Higher number = higher priority


class DataLoader:
    """Handles loading and validation of input data."""
    
    def __init__(self):
        self.trucks: List[Truck] = []
        self.delivery_points: List[DeliveryPoint] = []
    
    def load_trucks(self, file_path: str) -> List[Truck]:
        """
        Load truck data from JSON file.
        
        Args:
            file_path: Path to trucks JSON file
            
        Returns:
            List of Truck objects
            
        Raises:
            FileNotFoundError: If file doesn't exist
            ValueError: If data format is invalid
        """
        if not os.path.exists(file_path):
            raise FileNotFoundError(f"Trucks file not found: {file_path}")
        
        try:
            with open(file_path, 'r', encoding='utf-8') as f:
                trucks_data = json.load(f)
            
            trucks = []
            for truck_data in trucks_data:
                truck = Truck(
                    id=truck_data['id'],
                    start=truck_data['start'],
                    capacity=truck_data.get('capacity', 100),
                    speed_kmh=truck_data.get('speed_kmh', 40.0)
                )
                self._validate_truck(truck)
                trucks.append(truck)
            
            self.trucks = trucks
            return trucks
            
        except (json.JSONDecodeError, KeyError) as e:
            raise ValueError(f"Invalid truck data format: {e}")
    
    def load_delivery_points(self, file_path: str) -> List[DeliveryPoint]:
        """
        Load delivery points from JSON file.
        
        Args:
            file_path: Path to delivery points JSON file
            
        Returns:
            List of DeliveryPoint objects
            
        Raises:
            FileNotFoundError: If file doesn't exist
            ValueError: If data format is invalid
        """
        if not os.path.exists(file_path):
            raise FileNotFoundError(f"Delivery points file not found: {file_path}")
        
        try:
            with open(file_path, 'r', encoding='utf-8') as f:
                points_data = json.load(f)
            
            delivery_points = []
            for point_data in points_data:
                point = DeliveryPoint(
                    id=point_data['id'],
                    location=point_data['location'],
                    demand=point_data.get('demand', 1),
                    time_window_start=point_data.get('time_window_start', '09:00'),
                    time_window_end=point_data.get('time_window_end', '17:00'),
                    priority=point_data.get('priority', 1)
                )
                self._validate_delivery_point(point)
                delivery_points.append(point)
            
            self.delivery_points = delivery_points
            return delivery_points
            
        except (json.JSONDecodeError, KeyError) as e:
            raise ValueError(f"Invalid delivery points data format: {e}")
    
    def _validate_truck(self, truck: Truck) -> None:
        """Validate truck data."""
        if not isinstance(truck.start, list) or len(truck.start) != 2:
            raise ValueError(f"Truck {truck.id}: start must be [lat, lon] coordinates")
        
        lat, lon = truck.start
        if not (-90 <= lat <= 90) or not (-180 <= lon <= 180):
            raise ValueError(f"Truck {truck.id}: invalid coordinates {truck.start}")
        
        if truck.capacity <= 0:
            raise ValueError(f"Truck {truck.id}: capacity must be positive")
        
        if truck.speed_kmh <= 0:
            raise ValueError(f"Truck {truck.id}: speed must be positive")
    
    def _validate_delivery_point(self, point: DeliveryPoint) -> None:
        """Validate delivery point data."""
        if not isinstance(point.location, list) or len(point.location) != 2:
            raise ValueError(f"Point {point.id}: location must be [lat, lon] coordinates")
        
        lat, lon = point.location
        if not (-90 <= lat <= 90) or not (-180 <= lon <= 180):
            raise ValueError(f"Point {point.id}: invalid coordinates {point.location}")
        
        if point.demand <= 0:
            raise ValueError(f"Point {point.id}: demand must be positive")
        
        # Validate time format
        try:
            datetime.strptime(point.time_window_start, '%H:%M')
            datetime.strptime(point.time_window_end, '%H:%M')
        except ValueError:
            raise ValueError(f"Point {point.id}: invalid time format (use HH:MM)")
    
    def generate_sample_data(self, 
                           num_trucks: int = 3, 
                           num_deliveries: int = 10,
                           center_lat: float = 19.0760,
                           center_lon: float = 72.8777,
                           radius_km: float = 20) -> tuple[List[Truck], List[DeliveryPoint]]:
        """
        Generate sample data for testing.
        
        Args:
            num_trucks: Number of trucks to generate
            num_deliveries: Number of delivery points to generate
            center_lat: Center latitude for data generation
            center_lon: Center longitude for data generation
            radius_km: Radius in km for random point generation
            
        Returns:
            Tuple of (trucks, delivery_points)
        """
        import random
        import math
        
        trucks = []
        delivery_points = []
        
        # Generate trucks
        for i in range(num_trucks):
            # Random position within radius
            angle = random.uniform(0, 2 * math.pi)
            distance = random.uniform(0, radius_km / 111)  # Approximate conversion
            
            lat = center_lat + distance * math.cos(angle)
            lon = center_lon + distance * math.sin(angle)
            
            truck = Truck(
                id=i,
                start=[lat, lon],
                capacity=random.randint(80, 150),
                speed_kmh=random.uniform(35, 50)
            )
            trucks.append(truck)
        
        # Generate delivery points
        for i in range(num_deliveries):
            # Random position within radius
            angle = random.uniform(0, 2 * math.pi)
            distance = random.uniform(0, radius_km / 111)
            
            lat = center_lat + distance * math.cos(angle)
            lon = center_lon + distance * math.sin(angle)
            
            # Random time windows
            start_hour = random.randint(9, 14)
            end_hour = random.randint(start_hour + 2, 17)
            
            point = DeliveryPoint(
                id=100 + i,
                location=[lat, lon],
                demand=random.randint(5, 25),
                time_window_start=f"{start_hour:02d}:00",
                time_window_end=f"{end_hour:02d}:00",
                priority=random.randint(1, 3)
            )
            delivery_points.append(point)
        
        self.trucks = trucks
        self.delivery_points = delivery_points
        
        return trucks, delivery_points
    
    def save_data_to_files(self, trucks_file: str, deliveries_file: str) -> None:
        """Save current data to JSON files."""
        os.makedirs(os.path.dirname(trucks_file), exist_ok=True)
        os.makedirs(os.path.dirname(deliveries_file), exist_ok=True)
        
        # Save trucks
        trucks_data = []
        for truck in self.trucks:
            trucks_data.append({
                'id': truck.id,
                'start': truck.start,
                'capacity': truck.capacity,
                'speed_kmh': truck.speed_kmh
            })
        
        with open(trucks_file, 'w', encoding='utf-8') as f:
            json.dump(trucks_data, f, indent=2)
        
        # Save delivery points
        points_data = []
        for point in self.delivery_points:
            points_data.append({
                'id': point.id,
                'location': point.location,
                'demand': point.demand,
                'time_window_start': point.time_window_start,
                'time_window_end': point.time_window_end,
                'priority': point.priority
            })
        
        with open(deliveries_file, 'w', encoding='utf-8') as f:
            json.dump(points_data, f, indent=2)
    
    def get_summary(self) -> Dict[str, Any]:
        """Get summary statistics of loaded data."""
        if not self.trucks or not self.delivery_points:
            return {"error": "No data loaded"}
        
        total_demand = sum(point.demand for point in self.delivery_points)
        total_capacity = sum(truck.capacity for truck in self.trucks)
        
        return {
            "trucks": {
                "count": len(self.trucks),
                "total_capacity": total_capacity,
                "avg_speed_kmh": sum(t.speed_kmh for t in self.trucks) / len(self.trucks)
            },
            "delivery_points": {
                "count": len(self.delivery_points),
                "total_demand": total_demand,
                "avg_demand": total_demand / len(self.delivery_points)
            },
            "capacity_utilization": f"{(total_demand / total_capacity * 100):.1f}%"
        }


if __name__ == "__main__":
    # Example usage
    loader = DataLoader()
    
    # Generate and save sample data
    trucks, deliveries = loader.generate_sample_data()
    
    os.makedirs("data", exist_ok=True)
    loader.save_data_to_files("data/trucks.json", "data/deliveries.json")
    
    print("Sample data generated:")
    print(json.dumps(loader.get_summary(), indent=2))
