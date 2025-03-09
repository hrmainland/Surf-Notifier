# Surf Notifier

A Python tool that checks for optimal surfing conditions at specified surf spots and sends notifications when conditions are favorable.

## Features

- Retrieves swell and wind data from the StormGlass API
- Evaluates surf conditions based on:
  - Wind direction (offshore preferred)
  - Wind speed (< 1.5 m/s preferred)
  - Swell height (> 1m preferred)
- Sends notifications via Pushover when good surf conditions are detected
- Configurable for multiple surf spots
- Customizable time windows (default 6am-7pm)

## Requirements

- Python 3
- Required packages: requests, pytz, dotenv, numpy, pandas

## Setup

1. Clone this repository
2. Install dependencies: `pip install -r requirements.txt`
3. Create a `.env` file with the following keys:
   ```
   STORMGLASS_KEY=your_stormglass_api_key
   PUSHOVER_TOKEN=your_pushover_token
   PUSHOVER_USER=your_pushover_user_key
   ```

## Usage

Run the script to check conditions and send notifications:

```
python good_surf.py
```

## Configuration

You can modify the following parameters in the script:
- `WIND_RANGE`: Range in degrees for acceptable wind direction
- `SWELL_RANGE`: Range in degrees for acceptable swell direction
- `MIN_WIND_SPEED`: Minimum acceptable wind speed in m/s
- `MIN_SWELL_HEIGHT`: Minimum acceptable swell height in meters
- `MIN_GOOD_HOURS`: Minimum consecutive hours needed for notification
- `START_HOUR`/`END_HOUR`: Time window to check for conditions
- `DEVICES`: List of Pushover devices to notify