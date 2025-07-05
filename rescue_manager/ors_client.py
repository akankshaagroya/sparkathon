"""
OpenRouteService (ORS) API Client for Real Road Routing
Handles real driving routes, distances, and ETAs for rescue operations
"""

import os
import requests
import logging
from typing import Dict, List, Optional, Tuple
from dotenv import load_dotenv

# Load environment variables
load_dotenv()

logger = logging.getLogger(__name__)

class ORSClient:
    """Client for OpenRouteService API"""
    
    def __init__(self):
        self.api_key = os.getenv("ORS_API_KEY")
        self.base_url = "https://api.openrouteservice.org/v2"
        
        if not self.api_key:
            logger.warning("ORS_API_KEY not found in environment. Using fallback routing.")
            self.api_key = None
    
    def get_route(self, 
                  start_coords: Tuple[float, float], 
                  end_coords: Tuple[float, float],
                  profile: str = "driving-car") -> Optional[Dict]:
        """
        Get real driving route between two points
        
        Args:
            start_coords: (lat, lon) of starting point
            end_coords: (lat, lon) of ending point  
            profile: ORS profile (driving-car, driving-hgv, etc.)
            
        Returns:
            Dict with route info: {
                'distance': float,  # km
                'duration': float,  # seconds
                'geometry': str,    # encoded polyline
                'coordinates': List[List[float]]  # decoded coordinates
            }
        """
        if not self.api_key:
            return self._fallback_route(start_coords, end_coords)
        
        try:
            url = f"{self.base_url}/directions/{profile}/geojson"
            
            payload = {
                "coordinates": [
                    [start_coords[1], start_coords[0]],  # ORS expects [lon, lat]
                    [end_coords[1], end_coords[0]]
                ],
                "instructions": False,
                "geometry": True,
                "geometry_format": "polyline",
                "elevation": False
            }
            
            headers = {
                "Authorization": self.api_key,
                "Content-Type": "application/json"
            }
            
            response = requests.post(url, json=payload, headers=headers, timeout=10)
            response.raise_for_status()
            
            data = response.json()
            
            if data.get("features") and len(data["features"]) > 0:
                feature = data["features"][0]
                properties = feature["properties"]
                geometry = feature["geometry"]
                
                # Decode polyline coordinates
                coordinates = self._decode_polyline(geometry["coordinates"])
                
                return {
                    "distance": properties["summary"]["distance"] / 1000,  # Convert to km
                    "duration": properties["summary"]["duration"],  # seconds
                    "geometry": geometry["coordinates"],  # encoded polyline
                    "coordinates": coordinates  # decoded coordinates
                }
            
        except Exception as e:
            logger.error(f"ORS API error: {e}")
            return self._fallback_route(start_coords, end_coords)
    
    def _fallback_route(self, start_coords: Tuple[float, float], 
                       end_coords: Tuple[float, float]) -> Dict:
        """Fallback route calculation when ORS is not available"""
        # Simple geodesic distance calculation
        import math
        
        lat1, lon1 = start_coords
        lat2, lon2 = end_coords
        
        # Haversine formula
        R = 6371  # Earth's radius in km
        
        lat1_rad = math.radians(lat1)
        lat2_rad = math.radians(lat2)
        delta_lat = math.radians(lat2 - lat1)
        delta_lon = math.radians(lon2 - lon1)
        
        a = (math.sin(delta_lat/2) * math.sin(delta_lat/2) +
             math.cos(lat1_rad) * math.cos(lat2_rad) *
             math.sin(delta_lon/2) * math.sin(delta_lon/2))
        c = 2 * math.atan2(math.sqrt(a), math.sqrt(1-a))
        distance = R * c
        
        # Add 20% for road distance vs straight line
        road_distance = distance * 1.2
        
        # Estimate duration (assuming 40 km/h average speed)
        duration = (road_distance / 40) * 3600  # seconds
        
        # Create simple straight line coordinates
        coordinates = [list(start_coords), list(end_coords)]
        
        return {
            "distance": road_distance,
            "duration": duration,
            "geometry": None,
            "coordinates": coordinates
        }
    
    def _decode_polyline(self, encoded_polyline: str) -> List[List[float]]:
        """Decode Google-style polyline to coordinates"""
        # This is a simplified decoder - in production you'd use a proper library
        # For now, we'll return the coordinates as-is if they're already decoded
        if isinstance(encoded_polyline, list):
            return encoded_polyline
        
        # If it's actually encoded, we'd decode it here
        # For simplicity, return empty list
        return []

# Global ORS client instance
ors_client = ORSClient() 