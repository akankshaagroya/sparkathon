#!/usr/bin/env python3
"""
Configuration file for Cold Chain Dataset Generator
Edit these values to customize dataset generation
"""

# =============================================================================
# BASIC CONFIGURATION
# =============================================================================

# Number of trucks and events to generate
NUM_TRUCKS = 100
NUM_EVENTS = 15000
SIMULATION_DURATION_HOURS = 24

# Output directory
OUTPUT_DIR = "output"

# =============================================================================
# GEOGRAPHICAL CONFIGURATION
# =============================================================================

# GPS boundaries (currently set to Arkansas)
# To change to India, update these coordinates:
GPS_BOUNDS = {
    # # Arkansas boundaries
    # "lat_min": 33.004106,
    # "lat_max": 36.4996,
    # "lon_min": -94.6178,
    # "lon_max": -89.6444
    
    # Uncomment below for India boundaries:
    "lat_min": 8.4,
    "lat_max": 37.6,
    "lon_min": 68.7,
    "lon_max": 97.25
}

# Regional codes for trucks
REGIONS = ["IN-NORTH", "IN-SOUTH", "IN-EAST", "IN-WEST", "IN-CENTRAL"]
# For India, you might want: 

# =============================================================================
# TEMPERATURE CONFIGURATION
# =============================================================================

# Temperature ranges for different product categories (in Celsius)
TEMPERATURE_RANGES = {
    "frozen": (-18, -15),      # Frozen goods like ice cream
    "refrigerated": (2, 8),    # Dairy, meat, pharmaceuticals
    "ambient": (15, 25)        # Non-perishable goods
}

# =============================================================================
# PRODUCT CONFIGURATION
# =============================================================================

# Product categories with perishability scores (1-10, where 10 is most perishable)
# You can add or modify products here
PRODUCTS = {
    # Core required products
    "milk": 8,
    "meat": 9,
    "ice_cream": 10,
    "fruits": 6,
    "vegetables": 5,
    "yogurt": 7,
    
    # Additional products (25 more as requested)
    "cheese": 6,
    "fish": 9,
    "chicken": 9,
    "eggs": 6,
    "paneer": 8,
    "butter": 5,
    "cream": 8,
    "frozen_foods": 9,
    "berries": 8,
    "lettuce": 7,
    "tomatoes": 5,
    "carrots": 4,
    "broccoli": 6,
    "spinach": 8,
    "bacon": 7,
    "sausage": 7,
    "deli_meat": 8,
    "soup": 3,
    "juice": 4,
    "pharmaceuticals": 9,
    "vaccines": 10,
    "blood_products": 10,
    "curd": 7,
    "lassi": 6,
    "tofu": 7,
    "amras": 5,
    "idli_dosa_batter": 7
}

# =============================================================================
# TRUCK CONFIGURATION
# =============================================================================

# Truck capacity range (in kg)
TRUCK_CAPACITY_MIN = 1000
TRUCK_CAPACITY_MAX = 5000

# Truck types
TRUCK_TYPES = ["electric", "diesel"]

# Truck health statuses
TRUCK_HEALTH_STATUSES = ["Healthy", "Rescuing", "Broken Down"]

# OS version format
TRUCK_OS_VERSION_MAJOR_RANGE = (1, 5)
TRUCK_OS_VERSION_MINOR_RANGE = (0, 9)
TRUCK_OS_VERSION_PATCH_RANGE = (0, 9)

# =============================================================================
# FAULT INJECTION CONFIGURATION
# =============================================================================

# Probability of fault injection per event (0.1 = 10% chance)
FAULT_INJECTION_PROBABILITY = 0.1

# Types of faults to inject
FAULT_TYPES = [
    "cold_chain_breach",
    "engine_stall",
    "low_battery",
    "rescuing_mode",
    "shock_event",
    "none"
]

# Battery level thresholds
LOW_BATTERY_THRESHOLD = 5.0
CRITICAL_BATTERY_THRESHOLD = 1.0

# =============================================================================
# BATCH AND DELIVERY CONFIGURATION
# =============================================================================

# Number of batches per truck
BATCHES_PER_TRUCK_MIN = 1
BATCHES_PER_TRUCK_MAX = 4

# Batch volume and weight ranges
BATCH_VOLUME_MIN = 50      # liters
BATCH_VOLUME_MAX = 500     # liters
BATCH_WEIGHT_MIN = 25      # kg
BATCH_WEIGHT_MAX = 300     # kg

# Priority levels
PRIORITY_LEVELS = ["High", "Medium", "Low"]

# Delivery stops per batch
DELIVERY_STOPS_MIN = 1
DELIVERY_STOPS_MAX = 4

# ETA calculation (hours ahead)
ETA_BASE_HOURS_MIN = 1
ETA_BASE_HOURS_MAX = 48
ETA_STOP_INTERVAL_MIN = 2
ETA_STOP_INTERVAL_MAX = 6

# =============================================================================
# REAL-TIME SIMULATION CONFIGURATION
# =============================================================================

# Default speed multiplier for real-time simulation
DEFAULT_SPEED_MULTIPLIER = 1.0

# Event generation intervals
EVENT_INTERVAL_VARIATION = 0.2  # 20% variation in timing

# =============================================================================
# ALERT CONFIGURATION
# =============================================================================

# Alert levels
ALERT_LEVELS = {
    "none": 0,
    "low": 1,
    "medium": 2,
    "high": 3
}

# =============================================================================
# HELPER FUNCTIONS
# =============================================================================

def get_config():
    """Return the complete configuration as a dictionary"""
    return {
        "num_trucks": NUM_TRUCKS,
        "num_events": NUM_EVENTS,
        "simulation_duration_hours": SIMULATION_DURATION_HOURS,
        "output_dir": OUTPUT_DIR,
        "gps_bounds": GPS_BOUNDS,
        "regions": REGIONS,
        "temperature_ranges": TEMPERATURE_RANGES,
        "products": PRODUCTS,
        "truck_capacity_range": (TRUCK_CAPACITY_MIN, TRUCK_CAPACITY_MAX),
        "truck_types": TRUCK_TYPES,
        "truck_health_statuses": TRUCK_HEALTH_STATUSES,
        "fault_injection_probability": FAULT_INJECTION_PROBABILITY,
        "fault_types": FAULT_TYPES,
        "priority_levels": PRIORITY_LEVELS,
        "batch_config": {
            "per_truck_range": (BATCHES_PER_TRUCK_MIN, BATCHES_PER_TRUCK_MAX),
            "volume_range": (BATCH_VOLUME_MIN, BATCH_VOLUME_MAX),
            "weight_range": (BATCH_WEIGHT_MIN, BATCH_WEIGHT_MAX)
        },
        "delivery_config": {
            "stops_range": (DELIVERY_STOPS_MIN, DELIVERY_STOPS_MAX),
            "eta_base_range": (ETA_BASE_HOURS_MIN, ETA_BASE_HOURS_MAX),
            "eta_interval_range": (ETA_STOP_INTERVAL_MIN, ETA_STOP_INTERVAL_MAX)
        }
    }

# Usage examples:
# To change location to India:
# GPS_BOUNDS = {"lat_min": 8.4, "lat_max": 37.6, "lon_min": 68.7, "lon_max": 97.25}
# REGIONS = ["IN-NORTH", "IN-SOUTH", "IN-EAST", "IN-WEST", "IN-CENTRAL"]

# To increase dataset size:
# NUM_TRUCKS = 100
# NUM_EVENTS = 10000

# To add more products:
# PRODUCTS["new_product"] = perishability_score 