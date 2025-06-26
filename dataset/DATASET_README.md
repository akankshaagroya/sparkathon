# Cold Chain Logistics Dataset Generator

A comprehensive synthetic dataset generator for cold chain logistics operations across India, designed to simulate real-time monitoring of refrigerated trucks transporting perishable goods including traditional Indian dairy products and global food items.

## 🚛 Features

- **100 Unique Trucks**: Each with detailed metadata including capacity, health status, and maintenance records
- **15,000+ Events**: Real-time telemetry data with GPS coordinates, temperature, humidity, and fault scenarios
- **33 Product Types**: Including traditional Indian products (paneer, curd, lassi, idli_dosa_batter, amras) plus global items (milk, meat, ice cream, fruits, vegetables, yogurt, pharmaceuticals)
- **Fault Injection**: Realistic scenarios including cold chain breaches, engine stalls, low battery, and rescuing operations
- **Multiple Output Formats**: Both CSV and JSON formats for compatibility with different systems
- **Real-time Simulation**: Stream events as they would occur in real-time operations
- **Fully Configurable**: Easy-to-edit configuration file for customizing all parameters
- **India-Optimized**: Pre-configured for Indian market with regional coverage and local products

## 🇮🇳 Indian Market Focus

This dataset generator is specifically designed for the Indian cold chain logistics market:

- **Geographic Coverage**: Entire Indian subcontinent (Kashmir to Kanyakumari, Gujarat to Arunachal Pradesh)
- **Regional Distribution**: 5 zones (North, South, East, West, Central) matching logistics networks
- **Local Products**: Traditional Indian dairy and food items alongside global products
- **Scale**: 100 trucks and 15,000 events representing a mid-size logistics operation

### Indian Products Included:

- **Paneer**: Fresh cottage cheese (perishability: 8/10)
- **Curd**: Yogurt-based dairy product (perishability: 7/10)
- **Lassi**: Traditional yogurt drink (perishability: 6/10)
- **Idli_dosa_batter**: Fermented rice/lentil batter (perishability: 7/10)
- **Amras**: Mango pulp product (perishability: 5/10)

## 📦 Dataset Structure

### Event Records

Each event contains:

- `truck_id`: Unique truck identifier
- `timestamp`: Event timestamp
- `gps_lat`, `gps_lon`: GPS coordinates (covers entire Indian subcontinent: 8.4°-37.6°N, 68.7°-97.25°E)
- `temperature_c`: Internal temperature in Celsius
- `humidity_percent`: Humidity level
- `battery_level_percent`: Battery charge level
- `shock_event`: Boolean for sudden jolts/shocks
- `refrigeration_status`: On/Off status
- `cold_chain_status`: Derived status (NORMAL/BREACH/OVERCOOLED)
- `engine_status`: On/Off/Stalled
- `nearby_charger_available`: Boolean (EV trucks only)
- `distance_to_next_charger_km`: Distance to charger (EV trucks only)
- `event_type`: normal/fault/shock/rescuing
- `alert_level`: none/low/medium/high

### Truck Metadata

- `truck_id`: Unique identifier
- `total_capacity_kg`, `used_capacity_kg`: Capacity information
- `last_maintenance_date`: Last maintenance date
- `truck_os_version`: Operating system version
- `region_code`: Indian regional assignment (IN-NORTH, IN-SOUTH, IN-EAST, IN-WEST, IN-CENTRAL)
- `truck_health_status`: Healthy/Rescuing/Broken Down
- `truck_type`: electric/diesel
- `batches`: List of cargo batches

### Batch Information

- `batch_id`: Unique batch identifier
- `item_type`: Product category
- `perishability_score`: Scale 1-10
- `volume_liters`, `weight_kg`: Physical dimensions
- `priority_level`: High/Medium/Low
- `temperature_requirement`: frozen/refrigerated/ambient
- `delivery_stops`: List of delivery locations with ETAs

## 🚀 Quick Start

### 1. Installation

```bash
# Install Python dependencies
pip install -r requirements.txt
```

### 2. Generate Dataset

```bash
# Generate complete dataset (CSV + JSON)
python generate_dataset.py

# Files will be created in the 'output' directory:
# - trucks_metadata.csv / .json
# - events.csv / .json
# - batches.csv
# - complete_dataset.json
```

### 3. Real-time Simulation

```bash
# Run real-time simulation (console output)
python realtime_simulator.py

# Save to CSV in real-time
python realtime_simulator.py --output-csv output/live_events.csv

# Run at 5x speed
python realtime_simulator.py --speed 5.0 --output-json output/live_events.json
```

## ⚙️ Configuration

Edit `config.py` to customize the dataset:

### Change Geographic Location

```python
# For other regions (e.g., Arkansas)
GPS_BOUNDS = {
    "lat_min": 33.004106,
    "lat_max": 36.4996,
    "lon_min": -94.6178,
    "lon_max": -89.6444
}
REGIONS = ["AR-NW", "AR-NE", "AR-SW", "AR-SE", "AR-CENTRAL"]

# Current default is India:
# GPS_BOUNDS = {"lat_min": 8.4, "lat_max": 37.6, "lon_min": 68.7, "lon_max": 97.25}
# REGIONS = ["IN-NORTH", "IN-SOUTH", "IN-EAST", "IN-WEST", "IN-CENTRAL"]
```

### Increase Dataset Size

```python
NUM_TRUCKS = 200  # Currently set to 100
NUM_EVENTS = 20000  # Currently set to 15000
```

### Add Custom Products

```python
PRODUCTS["custom_product"] = 8  # perishability score 1-10

# Current Indian products included:
# paneer, curd, lassi, idli_dosa_batter, amras
```

### Adjust Fault Rates

```python
FAULT_INJECTION_PROBABILITY = 0.15  # 15% chance per event
```

## 📊 Output Files

### CSV Files

- `trucks_metadata.csv`: Truck information with flattened batch data
- `events.csv`: All telemetry events
- `batches.csv`: Detailed batch information with truck assignments

### JSON Files

- `complete_dataset.json`: Full dataset with hierarchical structure
- `trucks_metadata.json`: Truck data with nested batches and delivery stops
- `events.json`: All events with full metadata

## 🔧 Fault Scenarios

The generator includes realistic fault injection:

1. **Cold Chain Breach**: Temperature exceeds threshold while refrigeration is off
2. **Engine Stall**: Engine failure requiring assistance
3. **Low Battery**: Battery level drops below 5%
4. **Rescuing Mode**: Truck assists another truck by picking up its cargo
5. **Shock Events**: Sudden jolts that might damage sensitive cargo

## 📈 Dashboard & Analytics Ready

The dataset is designed for:

- **Real-time Dashboards**: Monitor fleet status, temperature alerts, and delivery progress
- **Decision Engines**: Automated responses to cold chain breaches and equipment failures
- **Route Optimization**: Historical and real-time data for route planning
- **Predictive Maintenance**: Truck health monitoring and maintenance scheduling
- **Compliance Reporting**: Temperature and timing compliance for regulatory requirements

## 🔄 Real-time Integration

The `realtime_simulator.py` can be integrated with:

- **Message Queues**: Apache Kafka, RabbitMQ
- **Databases**: InfluxDB, MongoDB, PostgreSQL
- **APIs**: REST endpoints, WebSocket streams
- **Visualization**: Grafana, Tableau, custom dashboards

## 📝 Usage Examples

### Basic Dataset Generation

```python
from generate_dataset import ColdChainDataGenerator

generator = ColdChainDataGenerator()
generator.generate_dataset()
```

### Custom Configuration

```python
from config import get_config
import json

# Load and modify configuration
config = get_config()
config["num_trucks"] = 150
config["gps_bounds"] = {"lat_min": 33.004106, "lat_max": 36.4996, "lon_min": -94.6178, "lon_max": -89.6444}
config["regions"] = ["AR-NW", "AR-NE", "AR-SW", "AR-SE", "AR-CENTRAL"]

# Generate with custom config
generator = ColdChainDataGenerator()
generator.CONFIG = config
generator.generate_dataset()
```

### Real-time Event Processing

```python
from realtime_simulator import RealTimeSimulator

def process_event(event):
    if event["alert_level"] == "high":
        print(f"ALERT: {event['truck_id']} has {event['event_type']}")
        # Send to alerting system

    # Store in database
    # Update dashboard
    # Trigger workflows

simulator = RealTimeSimulator(speed_multiplier=2.0)
simulator.start_simulation(output_callback=process_event)
```

## 🏗️ Project Structure

```
dataset/
├── generate_dataset.py      # Main dataset generator
├── realtime_simulator.py    # Real-time event streaming
├── config.py               # Configuration settings
├── requirements.txt        # Python dependencies
├── README.md              # This file
└── output/                # Generated datasets
    ├── trucks_metadata.csv
    ├── trucks_metadata.json
    ├── events.csv
    ├── events.json
    ├── batches.csv
    └── complete_dataset.json
```

## 🔧 Customization

The generator is highly modular and extensible:

1. **Add New Product Types**: Update `PRODUCTS` in `config.py`
2. **Modify Temperature Ranges**: Adjust `TEMPERATURE_RANGES`
3. **Change Fault Scenarios**: Extend `inject_fault_scenario()` method
4. **Add Custom Fields**: Modify the event generation logic
5. **Integrate External APIs**: Add real weather data, traffic conditions, etc.

## 📞 Support

For questions, customizations, or integration support:

1. Check the configuration options in `config.py`
2. Review the code comments for implementation details
3. Modify the generators to meet your specific requirements
4. Use the real-time simulator for testing integration scenarios

---

**Note**: This dataset generator is optimized for Indian cold chain logistics operations with GPS coordinates covering the entire Indian subcontinent (8.4°-37.6°N, 68.7°-97.25°E) and includes traditional Indian dairy products like paneer, curd, lassi, and idli_dosa_batter. To adapt for other regions, modify the GPS_BOUNDS, REGIONS, and PRODUCTS in `config.py`.
