"""
Router module for real-world distance and time calculations.
Uses OpenRouteService API for accurate routing information.
"""

import os
import time
from typing import List, Dict, Tuple, Optional
import requests
from geopy.distance import geodesic
import numpy as np
from dataclasses import dataclass
from dotenv import load_dotenv

load_dotenv()


@dataclass
class RouteInfo:
    """Contains routing information between two points."""
    distance_m: float
    duration_s: float
    geometry: Optional[List[List[float]]] = None


class Router:
    """Handles real-world routing calculations using OpenRouteService API."""
    
    def __init__(self, api_key: Optional[str] = None, use_fallback: bool = True):
        """
        Initialize router with API key.
        
        Args:
            api_key: OpenRouteService API key
            use_fallback: Whether to use geodesic distance as fallback
        """
        self.api_key = api_key or os.getenv('OPENROUTESERVICE_API_KEY')
        self.use_fallback = use_fallback
        self.base_url = "https://api.openrouteservice.org/v2"
        self.session = requests.Session()
        
        if self.api_key:
            self.session.headers.update({
                'Authorization': self.api_key,
                'Content-Type': 'application/json'
            })
        
        # Rate limiting
        self.last_request_time = 0
        self.min_request_interval = 1.0  # seconds between requests
        
        # Cache for repeated calculations
        self.route_cache: Dict[str, RouteInfo] = {}
    
    def get_route_info(self, start: List[float], end: List[float], 
                      profile: str = "driving-car") -> RouteInfo:
        """
        Get routing information between two points.
        
        Args:
            start: [latitude, longitude] of start point
            end: [latitude, longitude] of end point
            profile: Routing profile (driving-car, driving-hgv, etc.)
            
        Returns:
            RouteInfo object with distance and duration
        """
        # Create cache key
        cache_key = f"{start[0]:.6f},{start[1]:.6f}-{end[0]:.6f},{end[1]:.6f}-{profile}"
        
        if cache_key in self.route_cache:
            return self.route_cache[cache_key]
        
        # Try API first if available
        if self.api_key:
            try:
                route_info = self._query_openrouteservice(start, end, profile)
                self.route_cache[cache_key] = route_info
                return route_info
            except Exception as e:
                print(f"API request failed: {e}")
                if not self.use_fallback:
                    raise
        
        # Fallback to geodesic distance
        if self.use_fallback:
            route_info = self._fallback_calculation(start, end)
            self.route_cache[cache_key] = route_info
            return route_info
        
        raise Exception("No routing method available")
    
    def _query_openrouteservice(self, start: List[float], end: List[float], 
                               profile: str) -> RouteInfo:
        """Query OpenRouteService API for route information."""
        # Rate limiting
        current_time = time.time()
        time_since_last = current_time - self.last_request_time
        if time_since_last < self.min_request_interval:
            time.sleep(self.min_request_interval - time_since_last)
        
        # Convert lat,lon to lon,lat for ORS
        coordinates = [[start[1], start[0]], [end[1], end[0]]]
        
        url = f"{self.base_url}/directions/{profile}"
        
        payload = {
            "coordinates": coordinates,
            "format": "json",
            "instructions": False,
            "geometry": True
        }
        
        response = self.session.post(url, json=payload, timeout=30)
        self.last_request_time = time.time()
        
        if response.status_code != 200:
            raise Exception(f"API error {response.status_code}: {response.text}")
        
        data = response.json()
        
        if not data.get('routes'):
            raise Exception("No route found")
        
        route = data['routes'][0]
        summary = route['summary']
        
        # Extract geometry if available
        geometry = None
        if 'geometry' in route:
            # Decode polyline or use coordinates directly
            geometry = route['geometry']
        
        return RouteInfo(
            distance_m=summary['distance'],
            duration_s=summary['duration'],
            geometry=geometry
        )
    
    def _fallback_calculation(self, start: List[float], end: List[float]) -> RouteInfo:
        """Calculate route using geodesic distance as fallback."""
        # Use geodesic distance
        distance_m = geodesic((start[0], start[1]), (end[0], end[1])).meters
        
        # Estimate duration based on average speed
        # Add 30% overhead for real-world conditions
        avg_speed_kmh = float(os.getenv('DEFAULT_SPEED_KMH', 40))
        avg_speed_ms = avg_speed_kmh * 1000 / 3600
        duration_s = (distance_m * 1.3) / avg_speed_ms
        
        return RouteInfo(
            distance_m=distance_m * 1.3,  # Add overhead for actual roads
            duration_s=duration_s
        )
    
    def calculate_distance_matrix(self, locations: List[List[float]], 
                                profile: str = "driving-car") -> Tuple[np.ndarray, np.ndarray]:
        """
        Calculate distance and time matrices for multiple locations.
        
        Args:
            locations: List of [lat, lon] coordinates
            profile: Routing profile
            
        Returns:
            Tuple of (distance_matrix_m, time_matrix_s)
        """
        n = len(locations)
        distance_matrix = np.zeros((n, n))
        time_matrix = np.zeros((n, n))
        
        # Try batch request if API is available
        if self.api_key and n <= 25:  # ORS free tier limit
            try:
                return self._batch_matrix_request(locations, profile)
            except Exception as e:
                print(f"Batch request failed, falling back to individual requests: {e}")
        
        # Individual requests
        for i in range(n):
            for j in range(n):
                if i == j:
                    continue
                
                route_info = self.get_route_info(locations[i], locations[j], profile)
                distance_matrix[i][j] = route_info.distance_m
                time_matrix[i][j] = route_info.duration_s
        
        return distance_matrix, time_matrix
    
    def _batch_matrix_request(self, locations: List[List[float]], 
                            profile: str) -> Tuple[np.ndarray, np.ndarray]:
        """Make batch matrix request to OpenRouteService."""
        # Convert to lon,lat format
        coordinates = [[loc[1], loc[0]] for loc in locations]
        
        url = f"{self.base_url}/matrix/{profile}"
        
        payload = {
            "locations": coordinates,
            "metrics": ["distance", "duration"],
            "units": "m"
        }
        
        response = self.session.post(url, json=payload, timeout=60)
        
        if response.status_code != 200:
            raise Exception(f"Matrix API error {response.status_code}: {response.text}")
        
        data = response.json()
        
        if 'distances' not in data or 'durations' not in data:
            raise Exception("Invalid matrix response")
        
        distance_matrix = np.array(data['distances'])
        time_matrix = np.array(data['durations'])
        
        return distance_matrix, time_matrix
    
    def get_route_geometry(self, start: List[float], end: List[float], 
                          profile: str = "driving-car") -> Optional[List[List[float]]]:
        """Get route geometry for visualization."""
        route_info = self.get_route_info(start, end, profile)
        return route_info.geometry
    
    def validate_coordinates(self, coordinates: List[float]) -> bool:
        """Validate that coordinates are within valid ranges."""
        if len(coordinates) != 2:
            return False
        
        lat, lon = coordinates
        return -90 <= lat <= 90 and -180 <= lon <= 180
    
    def get_cache_stats(self) -> Dict[str, int]:
        """Get cache statistics."""
        return {
            "cached_routes": len(self.route_cache),
            "cache_size_mb": len(str(self.route_cache)) / (1024 * 1024)
        }
    
    def clear_cache(self) -> None:
        """Clear the route cache."""
        self.route_cache.clear()


def create_router(api_key: Optional[str] = None) -> Router:
    """Factory function to create a router instance."""
    return Router(api_key=api_key)


if __name__ == "__main__":
    # Example usage
    router = Router()
    
    # Test coordinates (Mumbai area)
    start = [19.0760, 72.8777]  # Mumbai Central
    end = [19.0728, 72.8826]    # Nearby location
    
    try:
        route_info = router.get_route_info(start, end)
        print(f"Distance: {route_info.distance_m:.0f}m")
        print(f"Duration: {route_info.duration_s:.0f}s ({route_info.duration_s/60:.1f} min)")
        
        # Test matrix calculation
        locations = [
            [19.0760, 72.8777],
            [19.0728, 72.8826],
            [19.0800, 72.8800]
        ]
        
        dist_matrix, time_matrix = router.calculate_distance_matrix(locations)
        print("\nDistance matrix (m):")
        print(dist_matrix)
        print("\nTime matrix (s):")
        print(time_matrix)
        
    except Exception as e:
        print(f"Error: {e}")
        print("Make sure to set OPENROUTESERVICE_API_KEY in .env file")
