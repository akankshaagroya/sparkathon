from geopy.distance import geodesic

def get_distance_km(loc1, loc2):
    """Calculate distance between two geographical points in kilometers"""
    return geodesic(loc1, loc2).km

def get_eta_minutes(loc1, loc2):
    """Calculate estimated time of arrival in minutes based on distance and average speed"""
    distance = get_distance_km(loc1, loc2)
    avg_speed_kmh = 40  # Assume 40 km/h city speed
    eta = (distance / avg_speed_kmh) * 60
    return eta

def calculate_money_saved(failed_truck, items_transferred):
    """Calculate estimated money saved by successful rescue operation"""
    # Base cost per item type (in currency units)
    item_values = {
        "milk": 50,
        "fruit": 30,
        "meat": 80,
        "veggies": 25,
        "vegetables": 25,
        "dairy": 60,
        "frozen_goods": 70,
        "beverages": 40
    }
    
    total_value = 0
    for item in items_transferred:
        total_value += item_values.get(item, 35)  # Default value for unknown items
    
    # Add penalty avoidance cost (delivery failure penalty)
    penalty_avoidance = 1000
    
    return total_value + penalty_avoidance

def estimate_delivery_delay_cost(delay_hours, stops_affected):
    """
    Calculate estimated cost of delivery delays
    """
    # Cost per hour of delay per delivery stop
    delay_cost_per_hour_per_stop = 50
    
    # Customer satisfaction penalty (exponential with delay)
    satisfaction_penalty = min(delay_hours * 100, 500)  # Cap at 500
    
    total_cost = (delay_hours * stops_affected * delay_cost_per_hour_per_stop) + satisfaction_penalty
    
    return total_cost

def get_route_efficiency_score(rescue_truck, failed_truck):
    """
    Calculate how efficiently the rescue truck can integrate the failed truck's delivery
    into its existing route
    """
    # Simple heuristic based on geographical efficiency
    rescue_distance = get_distance_km(rescue_truck['location'], failed_truck['location'])
    
    # If rescue truck is very close, integration is efficient
    if rescue_distance <= 5:  # 5km threshold
        return 0.9
    elif rescue_distance <= 15:  # 15km threshold  
        return 0.6
    else:
        return 0.3
