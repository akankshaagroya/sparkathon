from utils import get_distance_km, get_eta_minutes, calculate_money_saved
import logging

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# Scoring formula weights
ALPHA = 3.0    # Distance factor weight
BETA = 1.5     # Stops remaining weight
GAMMA = 2.0    # Capacity available weight
DELTA = 5.0    # Cold chain reliability weight
EPSILON = 2.0  # ETA weight

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
    
    # Calculate score using weighted formula
    score = (ALPHA * distance_factor) - (BETA * stops_left) + (GAMMA * capacity_available) + (DELTA * cold_chain) - (EPSILON * eta / 60)
    
    logger.debug(f"Scoring truck {rescue_truck['id']} for rescue of {failed_truck['id']}: "
                f"distance={distance:.2f}km, stops={stops_left}, capacity={capacity_available:.2f}, "
                f"cold_chain={cold_chain:.2f}, eta={eta:.2f}min, score={score:.2f}")
    
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
    Determine if ETA can be preserved after rescue operation
    """
    # Calculate if rescue truck can reach failed truck quickly enough
    rescue_eta = get_eta_minutes(rescue_truck['location'], failed_truck['location'])
    
    # Simple heuristic: if rescue truck is close and has few stops, ETA can be preserved
    if rescue_eta <= 30 and rescue_truck['stopsRemaining'] <= 2:
        return True
    
    return False

def create_rescue_payload(failed_truck, rescue_truck, timestamp):
    """
    Create the rescue operation payload
    """
    eta_preserved = can_preserve_eta(rescue_truck, failed_truck)
    items_transferred = failed_truck.get('items', [])
    money_saved = calculate_money_saved(failed_truck, items_transferred)
    
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
            "rescueScore": round(score_truck(rescue_truck, failed_truck), 2)
        }
    }
    
    return payload
