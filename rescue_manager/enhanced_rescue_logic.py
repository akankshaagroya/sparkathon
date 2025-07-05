"""
Enhanced Rescue Logic with 6-Factor Scoring System
Real road routing with ORS API integration
"""

import logging
import time
from typing import Dict, List, Optional, Tuple
from datetime import datetime
from ors_client import ors_client

logger = logging.getLogger(__name__)

class EnhancedRescueLogic:
    """Enhanced rescue logic with 6-factor scoring and real road routing"""
    
    def __init__(self):
        self.scoring_weights = {
            "proximity": 0.25,        # Distance to failed truck
            "capacity": 0.20,         # Available cargo capacity
            "cold_chain": 0.20,       # Cold chain reliability
            "battery": 0.15,          # Battery level
            "delivery_window": 0.10,  # Delivery time flexibility
            "route_efficiency": 0.10  # Current route efficiency
        }
    
    def find_best_rescue_truck(self, failed_truck: Dict, available_trucks: List[Dict]) -> Optional[Dict]:
        """
        Find the best rescue truck using 6-factor scoring
        
        Args:
            failed_truck: The truck that needs rescue
            available_trucks: List of operational trucks that can rescue
            
        Returns:
            Best rescue truck with score, or None if no suitable truck
        """
        if not available_trucks:
            logger.warning("No available trucks for rescue")
            return None
        
        best_truck = None
        best_score = -1
        
        for truck in available_trucks:
            # Skip if truck is already rescuing
            if truck.get("status") == "RESCUING":
                continue
                
            score = self._calculate_rescue_score(failed_truck, truck)
            
            logger.info(f"Truck {truck['id']} rescue score: {score:.2f}")
            
            if score > best_score:
                best_score = score
                best_truck = truck
        
        if best_truck:
            best_truck["rescue_score"] = best_score
            logger.info(f"Best rescue truck: {best_truck['id']} (score: {best_score:.2f})")
        
        return best_truck
    
    def _calculate_rescue_score(self, failed_truck: Dict, rescue_truck: Dict) -> float:
        """Calculate rescue score using 6-factor system"""
        
        # 1. Proximity Score (0-100)
        distance = self._calculate_distance(
            failed_truck["location"], 
            rescue_truck["location"]
        )
        proximity_score = max(0, 100 - (distance * 10))  # Higher score for closer trucks
        
        # 2. Capacity Score (0-100)
        capacity_ratio = rescue_truck.get("capacityAvailable", 0) / rescue_truck.get("totalCapacity", 1000)
        capacity_score = capacity_ratio * 100
        
        # 3. Cold Chain Reliability Score (0-100)
        cold_chain_score = rescue_truck.get("coldChainReliability", 50)
        
        # 4. Battery Score (0-100)
        battery_score = rescue_truck.get("battery", 50)
        
        # 5. Delivery Window Score (0-100)
        # More stops = less flexible = lower score
        stops_remaining = rescue_truck.get("stopsRemaining", 5)
        delivery_window_score = max(0, 100 - (stops_remaining * 10))
        
        # 6. Route Efficiency Score (0-100)
        # Based on current route optimization
        route_efficiency_score = 80  # Placeholder - could be calculated from actual routes
        
        # Calculate weighted score
        total_score = (
            self.scoring_weights["proximity"] * proximity_score +
            self.scoring_weights["capacity"] * capacity_score +
            self.scoring_weights["cold_chain"] * cold_chain_score +
            self.scoring_weights["battery"] * battery_score +
            self.scoring_weights["delivery_window"] * delivery_window_score +
            self.scoring_weights["route_efficiency"] * route_efficiency_score
        )
        
        logger.debug(f"Truck {rescue_truck['id']} scores - Proximity: {proximity_score:.1f}, "
                    f"Capacity: {capacity_score:.1f}, Cold Chain: {cold_chain_score:.1f}, "
                    f"Battery: {battery_score:.1f}, Delivery: {delivery_window_score:.1f}, "
                    f"Route: {route_efficiency_score:.1f}, Total: {total_score:.1f}")
        
        return total_score
    
    def generate_rescue_route(self, rescue_truck: Dict, failed_truck: Dict, 
                            delivery_points: List[Dict]) -> Dict:
        """
        Generate real rescue route using ORS API
        
        Args:
            rescue_truck: The truck performing the rescue
            failed_truck: The truck being rescued
            delivery_points: List of delivery points to visit after rescue
            
        Returns:
            Dict with route information
        """
        try:
            # Get route from rescue truck to failed truck
            rescue_route = ors_client.get_route(
                rescue_truck["location"],
                failed_truck["location"],
                profile="driving-hgv"  # Heavy goods vehicle profile
            )
            
            if not rescue_route:
                logger.error("Failed to generate rescue route")
                return None
            
            # Calculate total route including delivery points
            total_distance = rescue_route["distance"]
            total_duration = rescue_route["duration"]
            route_coordinates = rescue_route["coordinates"]
            
            # Add delivery points to route (simplified - in production you'd optimize this)
            for delivery_point in delivery_points[:3]:  # Limit to first 3 delivery points
                if delivery_point.get("lat") and delivery_point.get("lon"):
                    delivery_coords = (delivery_point["lat"], delivery_point["lon"])
                    
                    # Get route from failed truck to delivery point
                    delivery_route = ors_client.get_route(
                        failed_truck["location"],
                        delivery_coords,
                        profile="driving-hgv"
                    )
                    
                    if delivery_route:
                        total_distance += delivery_route["distance"]
                        total_duration += delivery_route["duration"]
                        # In production, you'd merge the route coordinates properly
            
            # Convert duration to minutes
            eta_minutes = int(total_duration / 60)
            
            rescue_info = {
                "rescue_truck_id": rescue_truck["id"],
                "failed_truck_id": failed_truck["id"],
                "distance_km": round(total_distance, 1),
                "eta_minutes": eta_minutes,
                "route_coordinates": route_coordinates,
                "total_duration_seconds": total_duration,
                "delivery_points_count": len(delivery_points[:3]),
                "route_type": "ORS_API" if ors_client.api_key else "Fallback",
                "timestamp": int(time.time())
            }
            
            logger.info(f"Rescue route generated: {rescue_truck['id']} → {failed_truck['id']} "
                       f"(Distance: {total_distance:.1f}km, ETA: {eta_minutes}min)")
            
            return rescue_info
            
        except Exception as e:
            logger.error(f"Error generating rescue route: {e}")
            return None
    
    def _calculate_distance(self, coord1: List[float], coord2: List[float]) -> float:
        """Calculate distance between two coordinates (simplified)"""
        import math
        
        lat1, lon1 = coord1
        lat2, lon2 = coord2
        
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
        
        return R * c
    
    def create_rescue_log_entry(self, failed_truck: Dict, rescue_truck: Dict, 
                               rescue_route: Dict) -> Dict:
        """Create a detailed log entry for the rescue operation"""
        
        failure_reasons = failed_truck.get("failureReasons", ["Unknown failure"])
        
        log_entry = {
            "timestamp": int(time.time()),
            "datetime": datetime.now().isoformat(),
            "type": "RESCUE_OPERATION",
            "failed_truck": {
                "id": failed_truck["id"],
                "location": failed_truck["location"],
                "failure_reasons": failure_reasons,
                "temperature": failed_truck.get("temp", 0),
                "battery": failed_truck.get("battery", 0)
            },
            "rescue_truck": {
                "id": rescue_truck["id"],
                "location": rescue_truck["location"],
                "score": rescue_truck.get("rescue_score", 0),
                "capacity_available": rescue_truck.get("capacityAvailable", 0),
                "battery": rescue_truck.get("battery", 0)
            },
            "rescue_route": rescue_route,
            "status": "assigned"
        }
        
        return log_entry

# Global instance
enhanced_rescue_logic = EnhancedRescueLogic() 