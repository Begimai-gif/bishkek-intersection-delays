import os, csv, time, datetime as dt
import requests
import pandas as pd

KEY = os.environ["DGIS_KEY"]
URL = f"https://routing.api.2gis.com/routing/7.0.0/global?key={KEY}"
OUT = "data/delays.csv"

def route(lat1, lon1, lat2, lon2):
    body = {
        "points": [
            {"type": "stop", "lat": float(lat1), "lon": float(lon1)},
            {"type": "stop", "lat": float(lat2), "lon": float(lon2)},
        ],
        "transport": "driving",
        "route_mode": "fastest",
        "traffic_mode": "jam",
    }
    r = requests.post(URL, json=body, timeout=20)
    r.raise_for_status()
    res = r.json()["result"][0]
    return res["total_duration"], res["total_distance"]

def weather():
    r = requests.get("https://api.open-meteo.com/v1/forecast", params={
        "latitude": 42.87, "longitude": 74.59,
        "current": "temperature_2m,precipitation,snowfall,wind_speed_10m",
        "timezone": "UTC"}, timeout=20)
    r.raise_for_status()
    return r.json()["current"]

def main():
    segs = pd.read_csv("segments.csv", skipinitialspace=True)
    ts = dt.datetime.now(dt.timezone.utc).isoformat(timespec="seconds")
    try:
        wx = weather()
    except Exception as e:
        print("weather failed:", type(e).__name__)
        wx = {}

    os.makedirs("data", exist_ok=True)
    new_file = not os.path.exists(OUT)
    with open(OUT, "a", newline="") as f:
        w = csv.writer(f)
        if new_file:
            w.writerow(["ts_utc", "segment_id", "intersection", "direction",
                        "live_s", "length_m",
                        "temp_c", "precip_mm", "snow_cm", "wind_ms"])
        for row in segs.itertuples(index=False):
            try:
                live, length = route(row.lat_start, row.lon_start,
                                     row.lat_end, row.lon_end)
            except Exception as e:
                print("failed", row.segment_id, type(e).__name__)
                continue
            w.writerow([ts, row.segment_id, row.intersection, row.direction,
                        live, length,
                        wx.get("temperature_2m"), wx.get("precipitation"),
                        wx.get("snowfall"), wx.get("wind_speed_10m")])
            time.sleep(1.5)

if __name__ == "__main__":
    main()
