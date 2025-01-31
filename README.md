# Air Quality Analyzer

A Python package for monitoring and analyzing PM2.5 air quality data using the World Air Quality Index (WAQI) API. This tool allows you to collect real-time PM2.5 measurements from multiple monitoring stations within a specified geographical area.

## Features

- Real-time PM2.5 data collection from multiple stations
- Configurable sampling period and rate
- Concurrent data collection using thread pools
- Error handling and automatic retries
- Flexible logging levels
- Thread-safe operations

## Installation

You can install the package directly from GitHub:

```bash
pip install git+https://github.com/amirrezaes/AirQuality.git
```

Or clone the repository and install locally:

```bash
git clone https://github.com/amirrezaes/AirQuality.git
cd AirQuality
pip install .
```

## Usage

Here's a basic example of how to use the Air Quality Analyzer:

```python
from air_quality_analyzer.analyzer import calculate_average_pm25

# Initialize the analyzer with geographical bounds
analyzer = calculate_average_pm25(
    latitude_1=35.6892,    # Southern boundary
    longitude_1=51.3890,   # Western boundary
    latitude_2=35.7272,    # Northern boundary
    longitude_2=51.4258,   # Eastern boundary
    sampling_period=5,     # Duration in minutes
    sampling_rate=1        # Samples per minute
)

# Set your WAQI API token
analyzer.set_token("your-api-token")

# Start sampling (non-blocking)
analyzer.start_sampling(blocking=False)

print(analyzer.sampling_status())

# Get average PM2.5 when done
while analyzer.sampling_status() != analyzer.DONE:
    time.sleep(1)

result = analyzer.avg_pm25_all_sites()
print(f"Average PM2.5: {result}")

# Stop sampling manually
analyzer.stop_sampling()
```
Check [sample_code.py](https://github.com/amirrezaes/AirQuality/blob/main/sample_code.py) for more examples
## Configuration

The analyzer can be configured with several parameters:

- `sampling_period`: Duration of sampling in minutes (default: 5)
- `sampling_rate`: Number of samples per minute (default: 1)
- `thread_cnt`: Number of concurrent threads for data collection (default: 8)

You can also control logging verbosity:

```python
analyzer.set_logger_level('info')  # Options: 'info', 'error', 'critical'
```

## API Token

You'll need a WAQI API token to use this package. You can get one by registering at [WAQI API](https://aqicn.org/api/).

## States

The analyzer can be in one of these states:
- `IDLE`: Ready but not actively sampling
- `RUNNING`: Currently collecting samples
- `DONE`: Sampling completed successfully
- `FAILED`: Sampling failed due to an error
- `STOPPED`: Sampling was manually stopped

## Development and Test

To set up the development environment:

```bash
# Install development dependencies
pip install '.[test]'

# Run tests
pytest tests/test-air-quality.py

# or if you preffer unitest like me
python -m unittest tests\test-air-quality.py
```
