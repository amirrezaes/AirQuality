# CalculateAveragePM25

A class that calculates the average PM2.5 (fine particulate matter) values from multiple air quality monitoring stations within a specified geographical boundary using the World Air Quality Index (WAQI) API.

## Overview

This class enables periodic sampling of PM2.5 data from multiple air quality monitoring stations within a defined geographical area. It uses threading to efficiently collect data from multiple stations concurrently and supports configurable sampling periods and rates.

## Prerequisites

- Python>=3.10 (only tested on 3.11)
- Required packages (all standard):
  - requests
  - threading
  - concurrent.futures
  - logging

## Class Parameters

- `latitude_1` (float): First latitude coordinate of the bounding box
- `longitude_1` (float): First longitude coordinate of the bounding box
- `latitude_2` (float): Second latitude coordinate of the bounding box
- `longitude_2` (float): Second longitude coordinate of the bounding box
- `sampling_period` (int, optional): Total duration of sampling in minutes. Defaults to 5.
- `sampling_rate` (int, optional): Number of samples to collect per minute. Defaults to 1.

## States

The class maintains the following states:
- `IDLE`: Initial state or waiting for next sampling
- `RUNNING`: Currently collecting samples
- `DONE`: Sampling completed successfully
- `FAILED`: Sampling failed due to an error
- `STOPPED`: Sampling process was manually stopped

## Methods

### set_token(token: str)
Sets the WAQI API token required for making API requests.
```python
def set_token(token: str) -> None
```

### start_sampling(blocking: bool = False)
Initiates the PM2.5 sampling process.
```python
def start_sampling(blocking: bool = False) -> None
```
- `blocking`: If True, waits for all sampling to complete before returning

### stop_sampling()
Stops the ongoing sampling process and cleans up resources.
```python
def stop_sampling() -> None
```

### sampling_status()
Returns the current state of the sampling process.
```python
def sampling_status() -> str
```

### avg_pm25_all_sites()
Returns the calculated average PM2.5 value from all sampled sites.
```python
def avg_pm25_all_sites() -> float | None
```

### set_logger_level(lvl: str)
Sets the logging verbosity level.
```python
def set_logger_level(lvl: str) -> None
```
- `lvl`: Accepts 'info', 'error', or 'critical'

### clean_up()
Clears all collected data and resets the class state.
```python
def clean_up() -> None
```

## Usage Example

```python
# Create an instance for the Los Angeles area
calculator = CalculateAveragePM25(
    latitude_1=34.0522,  # LA downtown
    longitude_1=-118.2437,
    latitude_2=34.0689,  # Hollywood
    longitude_2=-118.3267,
    sampling_period=10,  # 10 minutes
    sampling_rate=2      # 2 samples per minute
)

# Set your WAQI API token
calculator.set_token("api-token")

# Start sampling
calculator.start_sampling()

# Check status
while calculator.sampling_status() != 'DONE':
    time.sleep(30)
    print(f"Current status: {calculator.sampling_status()}")

# Get results
avg_pm25 = calculator.avg_pm25_all_sites()
print(f"Average PM2.5: {avg_pm25}")

# Clean up
calculator.clean_up()
```