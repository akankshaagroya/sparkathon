# Rescue Manager System

This is a cold chain truck rescue management system that detects truck failures and assigns rescue operations automatically.

## Features

- **Failure Detection**: Monitors truck temperature, refrigeration status, and battery levels
- **Intelligent Rescue Assignment**: Uses a scoring algorithm to find the best rescue truck
- **ETA Preservation**: Attempts to maintain delivery schedules during rescue operations
- **Cost Calculation**: Estimates money saved through successful rescue operations
- **Comprehensive Logging**: Tracks all rescue operations with detailed logs
- **REST API**: Provides endpoints for integration with other systems

## Quick Start

1. Install dependencies:
```bash
pip install -r requirements.txt
```

2. Run the server:
```bash
uvicorn main:app --reload
```

3. Access the API:
- Main rescue endpoint: http://127.0.0.1:8000/run_rescue
- Truck status: http://127.0.0.1:8000/truck_status
- API documentation: http://127.0.0.1:8000/docs

## API Endpoints

### GET /run_rescue
Main rescue operation endpoint that:
- Detects failed trucks based on temperature, refrigeration, and battery criteria
- Finds the best rescue truck for each failed truck using a scoring algorithm
- Returns rescue operation payloads

### GET /truck_status
Returns current status of all trucks, including failed and operational trucks.

### GET /health
Health check endpoint.

### POST /update_truck_data
Updates the truck dataset with new information.

### GET /logs
Lists all rescue operation logs.

### GET /logs/{log_id}
Retrieves a specific rescue operation log.

## Failure Criteria

A truck is marked as FAILED if:
- Temperature > 8°C
- Refrigeration = False
- Battery < 5%

## Rescue Scoring Algorithm

The system uses a weighted scoring formula to select the best rescue truck:

```
Score = (α × distance_factor) - (β × stops_remaining) + (γ × capacity_available) + (δ × cold_chain_reliability) - (ε × eta_factor)
```

Where:
- α = 3.0 (Distance factor weight)
- β = 1.5 (Stops remaining weight)  
- γ = 2.0 (Capacity available weight)
- δ = 5.0 (Cold chain reliability weight)
- ε = 2.0 (ETA weight)

## Sample Output

```json
{
  "rescue": true,
  "fromTruck": "TRK_04",
  "toTruck": "TRK_07",
  "etaPreserved": true,
  "moneySaved": 2100,
  "itemsTransferred": ["milk", "fruit"],
  "timestamp": 1720345260,
  "rescueDetails": {
    "failureReasons": ["Battery too low: 3%"],
    "rescueDistance": 4.25,
    "rescueETA": 6.38,
    "rescueScore": 8.45
  }
}
```

## File Structure

- `main.py` - FastAPI application with REST endpoints
- `data.py` - Mock truck dataset for testing
- `rescue_logic.py` - Core rescue logic and scoring algorithms
- `utils.py` - Utility functions for distance and ETA calculations
- `logs/` - Directory for storing rescue operation logs
- `requirements.txt` - Python dependencies

## Configuration

Key parameters can be adjusted in `rescue_logic.py`:
- Temperature threshold
- Battery thresholds
- Scoring formula weights
- Minimum requirements for rescue trucks
