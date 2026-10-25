import os, csv, time, datetime as dt
import requests
import pandas as pd

KEYS = [k for k in (os.environ.get("DGIS_KEY"),
                    os.environ.get("DGIS_KEY_2"),
                    os.environ.get("DGIS_KEY_3")) if k]
OUT = "data/delays.csv"

def route(lat1, lon1, lat2, lon2, start):
    body = {
        "points": [
            {"type": "stop", "lat": float(lat1), "lon": float(lon1)},
            {"type": "stop", "lat": float(lat2), "lon": float(lon2)},
        ],
        "transport": "driving",
        "route_mode": "fastest",
        "traffic_mode": "jam",
    }
    err = "no keys"
    n = len(KEYS)
    for shift in range(n):
        key = KEYS[(start + shift) % n]
        url = f"https://routing.api.2gis.com/routing/7.0.0/global?key={key}"
        try:
            r = requests.post(url, json=body, timeout=20)
            if r.status_code == 200:
                result = r.json().get("result")
                if result:
                    return result[0]["total_duration"], result[0]["total_distance"]
                err = "empty result"
            else:
                err = f"HTTP {r.status_code}"
        except Exception as e:
            err = type(e).__name__
    raise RuntimeError(err)

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
        for i, row in enumerate(segs.itertuples(index=False)):
            try:
                live, length = route(row.lat_start, row.lon_start,
                                     row.lat_end, row.lon_end,
                                     i % max(len(KEYS), 1))
            except Exception as e:
                print("failed", row.segment_id, e)
                continue
            w.writerow([ts, row.segment_id, row.intersection, row.direction,
                        live, length,
                        wx.get("temperature_2m"), wx.get("precipitation"),
                        wx.get("snowfall"), wx.get("wind_speed_10m")])
            time.sleep(1.5)

if __name__ == "__main__":
    main()
