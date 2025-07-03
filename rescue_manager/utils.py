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
