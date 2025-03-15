import requests
import time
import pytz

import os

import numpy as np
import pandas as pd
from datetime import datetime, timezone, timedelta
import math

# # only required for dev
# import dotenv
# dotenv.load_dotenv()

WIND_RANGE = 100
SWELL_RANGE = 100
# in meters per second (*3.6 for kmph)
MIN_WIND_SPEED = 1.5
MIN_SWELL_HEIGHT = 1
MIN_GOOD_HOURS = 3
START_HOUR = 6
END_HOUR = 19

DEVICES = ["iphonexs", "pixel6a"]

STORMGLASS_KEY = os.getenv("STORMGLASS_KEY")
PUSHOVER_TOKEN = os.getenv("PUSHOVER_TOKEN")
PUSHOVER_USER = os.getenv("PUSHOVER_USER")

STORMGLASS_URL = "https://api.stormglass.io/v2/weather/point"
PUSHOVER_URL = "https://api.pushover.net/1/messages.json"


class SurfSpot:
    def __init__(self, name, lat, lng, direction):
        # direction is perpendicular to the shore, going out to sea (ie. offshore wind direction)
        self.name = name
        self.lat = lat
        self.lng = lng
        self.direction = direction


# for stormglass request


def unix_timestamp():
    melbourne_tz = pytz.timezone("Australia/Melbourne")
    now = datetime.today().astimezone(melbourne_tz)
    # Convert to UNIX timestamp
    return int(time.mktime(now.timetuple()))


def get_swell_data(surf_spot):
    params = {
        "params": "swellHeight,swellDirection,waveDirection,swellPeriod,windDirection,windSpeed",
        "start": unix_timestamp(),
        "lat": surf_spot.lat,
        "lng": surf_spot.lng,
    }
    headers = {"Authorization": STORMGLASS_KEY}

    response = requests.get(STORMGLASS_URL, params=params, headers=headers)
    if response.status_code != 200:
        print(response.json())
    print(f"Retrieved swell data for {surf_spot.name}")
    return response.json()


# for evaluation logic:
def readable_date(datetime_obj):
    # Format the date to match "Sunday 10th 4pm" style
    formatted_date_custom = datetime_obj.strftime("%A %-d")  # Day name and day number

    # Add ordinal suffix
    day = datetime_obj.day
    if 10 <= day <= 20 or day % 10 not in {1, 2, 3}:
        suffix = "th"
    else:
        suffix = {1: "st", 2: "nd", 3: "rd"}[day % 10]

    return f"{formatted_date_custom}{suffix}"


def avg_angle(angles):
    # Convert angles to x and y components
    x = sum(math.cos(math.radians(a)) for a in angles)
    y = sum(math.sin(math.radians(a)) for a in angles)

    # Compute average angle in degrees
    avg_theta = math.degrees(math.atan2(y, x))

    # Ensure angle is in [0, 360)
    return round(avg_theta % 360)


def wind_direction_eval(df, spot):
    direction_list = [
        int(avg_angle(list(elem.values()))) for elem in df["windDirection"]
    ]
    half_wind_range = WIND_RANGE // 2
    return [
        int(
            elem
            in range(spot.direction - half_wind_range, spot.direction + half_wind_range)
        )
        for elem in direction_list
    ]


def wind_speed_eval(df, spot):
    return [
        int(np.mean(list(elem.values())) < MIN_WIND_SPEED) for elem in df["windSpeed"]
    ]


def wind_eval(df, spot):
    return [
        max(a, b)
        for a, b in zip(wind_direction_eval(df, spot), wind_speed_eval(df, spot))
    ]


def swell_height_eval(df):
    return [
        int(np.mean(list(elem.values())) > MIN_SWELL_HEIGHT)
        for elem in df["swellHeight"]
    ]


def final_eval(df, spot):
    return [min(a, b) for a, b in zip(wind_eval(df, spot), swell_height_eval(df))]


def get_df(surf_spot):
    df = pd.DataFrame(swell_data["hours"])
    melbourne_tz = pytz.timezone("Australia/Melbourne")

    df["time"] = df["time"].apply(
        lambda x: datetime.fromisoformat(x)
        .replace(tzinfo=timezone.utc)
        .astimezone(melbourne_tz)
    )

    df.set_index("time", inplace=True)

    df["windEval"] = wind_eval(df, surf_spot)
    df["swellEval"] = swell_height_eval(df)
    df["finalEval"] = final_eval(df, surf_spot)
    return df


def is_this_week(date: datetime):
    weekday_diff = date.weekday() - datetime.today().weekday()
    return (datetime.today() + timedelta(weekday_diff)).day == date.day


def get_good_groups(df):
    result = {}
    for day in range(1, 32):
        eval_df = df[["swellHeight", "finalEval"]][
            (df.index.day == day)
            & (df.index.hour >= START_HOUR)
            & (df.index.hour < END_HOUR)
        ]
        if len(eval_df) == 0:
            continue
        eval_df["swellHeight"] = eval_df["swellHeight"].apply(
            lambda x: round(np.mean(list(x.values())), 2)
        )
        date = eval_df.index[0]
        for i in range(len(eval_df) - MIN_GOOD_HOURS + 1):
            window = eval_df[i : i + MIN_GOOD_HOURS]
            good_hours = window["finalEval"].sum()
            if good_hours == MIN_GOOD_HOURS:
                result[date] = round(np.mean(window["swellHeight"]), 1)
                break
    return result


if __name__ == "__main__":

    sandy = SurfSpot("Sandy", -38.83, 146.118, 33)
    thirteenth = SurfSpot("13th Beach", -38.2889164, 144.4708001, 10)
    all_spots = [thirteenth, sandy]

    msg = ""

    for surf_spot in all_spots:

        swell_data = get_swell_data(surf_spot)
        df = get_df(surf_spot)
        pushover_data = get_good_groups(df)

        msg += f"{surf_spot.name}:\n"

        for date, swell_height in pushover_data.items():
            week_str = "this" if is_this_week(date) else "next"
            msg += f"{swell_height}m {week_str} {date.strftime('%A')}\n"

        if len(pushover_data) == 0:
            msg += "No clean surf conditions :(\n"
        msg += "\n"

    # remove last two newlines
    msg = msg[:-2]

    for device in DEVICES:

        response = requests.post(
            PUSHOVER_URL,
            params={
                "token": PUSHOVER_TOKEN,
                "user": PUSHOVER_USER,
                "title": f"Clean Surf Conditions",
                "message": msg,
                "device": device,
            },
        )
        if response.status_code != 200:
            print(response.json())
            break
        print(f"Sent notification for {surf_spot.name} to {device}\nmsg:\n{msg}")
