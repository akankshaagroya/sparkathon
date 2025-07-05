from utils import get_distance_km, get_eta_minutes, calculate_money_saved, estimate_delivery_delay_cost, get_route_efficiency_score
import logging

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# Enhanced scoring formula weights
ALPHA = 3.0    # Distance factor weight
BETA = 1.5     # Stops remaining weight  
GAMMA = 2.0    # Capacity available weight
DELTA = 5.0    # Cold chain reliability weight
EPSILON = 2.0  # ETA weight
ZETA = 4.0     # Delivery window impact weight (NEW)

# Failure detection thresholds
TEMP_THRESHOLD = 8  # Celsius
MIN_BATTERY = 5     # Percentage
MIN_RESCUE_BATTERY = 15  # Minimum battery for rescue truck
MIN_RESCUE_CAPACITY = 0.1  # Minimum capacity for rescue truck

def detect_failures(trucks):
    """
    Detect failed trucks based on temperature, refrigeration, and battery criteria
    """
    failed_trucks = []
    for truck in trucks:
        failure_reasons = []
        
        if truck['temp'] > TEMP_THRESHOLD:
            failure_reasons.append(f"Temperature too high: {truck['temp']}°C")
        
        if not truck['refrigeration']:
            failure_reasons.append("Refrigeration system failed")
        
        if truck['battery'] < MIN_BATTERY:
            failure_reasons.append(f"Battery too low: {truck['battery']}%")
        
        if failure_reasons:
            truck['status'] = 'FAILED'
            truck['failure_reasons'] = failure_reasons
            failed_trucks.append(truck)
            logger.info(f"Truck {truck['id']} failed: {', '.join(failure_reasons)}")
    
    return failed_trucks

def calculate_delivery_window_impact(rescue_truck, failed_truck):
    """
    Calculate impact on delivery windows for both rescue and existing deliveries
    Returns a normalized score (0-1, higher is better)
    """
    # Get rescue time to failed truck
    rescue_eta = get_eta_minutes(rescue_truck['location'], failed_truck['location'])
    
    # Estimate additional time for rescue operation
    transfer_time = 30  # 30 minutes for goods transfer
    total_rescue_time = rescue_eta + transfer_time
    
    # Calculate delay impact on rescue truck's remaining deliveries
    stops_remaining = rescue_truck['stopsRemaining']
    
    # Penalty for each stop that might be delayed
    delay_penalty = stops_remaining * (total_rescue_time / 60)  # Hours of delay
    
    # Normalize to 0-1 scale (lower delay = higher score)
    max_acceptable_delay = 2.0  # 2 hours max acceptable delay
    window_score = max(0, 1 - (delay_penalty / max_acceptable_delay))
    
    return window_score

def score_truck(rescue_truck, failed_truck):
    """
    Calculate rescue score for a truck based on multiple factors
    Higher score = better rescue candidate
    """
    distance = get_distance_km(rescue_truck['location'], failed_truck['location'])
    distance_factor = 1 / (distance + 0.1)  # Avoid division by zero
    
    stops_left = rescue_truck['stopsRemaining']
    capacity_available = rescue_truck['capacityAvailable'] / rescue_truck['totalCapacity']
    cold_chain = rescue_truck['coldChainReliability']
    eta = get_eta_minutes(rescue_truck['location'], failed_truck['location'])
    
    # NEW: Calculate delivery window impact
    delivery_window_score = calculate_delivery_window_impact(rescue_truck, failed_truck)
    
    # Normalize ETA factor (convert to 0-1 scale)
    max_acceptable_eta = 120  # 2 hours max
    eta_factor = max(0, 1 - (eta / max_acceptable_eta))
    
    # Normalize stops factor (fewer stops = higher score)
    max_stops = 10
    stops_factor = max(0, 1 - (stops_left / max_stops))
    
    # Enhanced scoring formula with proper normalization
    score = (
        ALPHA * distance_factor +
        BETA * stops_factor + 
        GAMMA * capacity_available + 
        DELTA * cold_chain + 
        EPSILON * eta_factor +
        ZETA * delivery_window_score  # NEW delivery window factor
    )
    
    logger.debug(f"Scoring truck {rescue_truck['id']} for rescue of {failed_truck['id']}: "
                f"distance={distance:.2f}km, stops={stops_left}, capacity={capacity_available:.2f}, "
                f"cold_chain={cold_chain:.2f}, eta={eta:.2f}min, delivery_window={delivery_window_score:.2f}, "
                f"score={score:.2f}")
    
    return score

def find_best_rescue(failed_truck, trucks):
    """
    Find the best rescue truck for a failed truck
    """
    # Filter candidates based on minimum requirements
    candidates = [
        t for t in trucks 
        if (t['status'] == 'OK' and 
            t['battery'] > MIN_RESCUE_BATTERY and 
            t['refrigeration'] and 
            t['capacityAvailable'] > MIN_RESCUE_CAPACITY and
            t['id'] != failed_truck['id'])  # Don't rescue self
    ]
    
    if not candidates:
        logger.warning(f"No suitable rescue trucks found for {failed_truck['id']}")
        return None
    
    # Score all candidates
    scored = []
    for truck in candidates:
        score = score_truck(truck, failed_truck)
        scored.append((truck, score))
    
    # Sort by score (highest first)
    scored.sort(key=lambda x: x[1], reverse=True)
    
    best_truck = scored[0][0]
    best_score = scored[0][1]
    
    logger.info(f"Best rescue truck for {failed_truck['id']}: {best_truck['id']} (score: {best_score:.2f})")
    
    return best_truck

def can_preserve_eta(rescue_truck, failed_truck):
    """
    Enhanced ETA preservation check with delivery window consideration
    """
    rescue_eta = get_eta_minutes(rescue_truck['location'], failed_truck['location'])
    transfer_time = 30  # minutes for goods transfer
    total_time = rescue_eta + transfer_time
    
    # Check multiple conditions for ETA preservation
    conditions = [
        rescue_eta <= 30,  # Quick rescue response
        rescue_truck['stopsRemaining'] <= 2,  # Few remaining stops
        total_time <= 60,  # Total operation under 1 hour
        rescue_truck['capacityAvailable'] >= 0.3  # Adequate capacity buffer
    ]
    
    # ETA can be preserved if at least 3 out of 4 conditions are met
    return sum(conditions) >= 3

def create_rescue_payload(failed_truck, rescue_truck, timestamp):
    """
    Create the rescue operation payload with enhanced metrics
    """
    from utils import estimate_delivery_delay_cost, get_route_efficiency_score
    
    eta_preserved = can_preserve_eta(rescue_truck, failed_truck)
    items_transferred = failed_truck.get('items', [])
    money_saved = calculate_money_saved(failed_truck, items_transferred)
    
    # Calculate delivery window impact
    delivery_window_score = calculate_delivery_window_impact(rescue_truck, failed_truck)
    
    # Estimate potential delay costs
    rescue_eta_hours = get_eta_minutes(rescue_truck['location'], failed_truck['location']) / 60
    delay_cost = estimate_delivery_delay_cost(rescue_eta_hours, rescue_truck['stopsRemaining'])
    
    # Route efficiency
    route_efficiency = get_route_efficiency_score(rescue_truck, failed_truck)
    
    payload = {
        "rescue": True,
        "fromTruck": failed_truck['id'],
        "toTruck": rescue_truck['id'],
        "etaPreserved": eta_preserved,
        "moneySaved": money_saved,
        "itemsTransferred": items_transferred,
        "timestamp": timestamp,
        "rescueDetails": {
            "failureReasons": failed_truck.get('failure_reasons', []),
            "rescueDistance": round(get_distance_km(rescue_truck['location'], failed_truck['location']), 2),
            "rescueETA": round(get_eta_minutes(rescue_truck['location'], failed_truck['location']), 2),
            "rescueScore": round(score_truck(rescue_truck, failed_truck), 2),
            "deliveryWindowScore": round(delivery_window_score, 2),
            "estimatedDelayCost": round(delay_cost, 2),
            "routeEfficiency": round(route_efficiency, 2),
            "keyFactors": {
                "proximity": f"{round(get_distance_km(rescue_truck['location'], failed_truck['location']), 2)} km",
                "coldChainStatus": "Working" if rescue_truck['refrigeration'] else "Failed",
                "availableCapacity": f"{round(rescue_truck['capacityAvailable'] * 100, 1)}%",
                "batteryLevel": f"{rescue_truck['battery']}%",
                "stopsRemaining": rescue_truck['stopsRemaining']
            }
        }
    }
    
    return payload
