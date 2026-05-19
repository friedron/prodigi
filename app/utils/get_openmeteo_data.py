import re
import openmeteo_requests
import pandas as pd
import requests_cache
from retry_requests import retry

def get_openmeteo_data(latitude, longitude, start_date, end_date, features):
  # Setup the Open-Meteo API client with cache and retry on error
  cache_session = requests_cache.CachedSession('.cache', expire_after = -1)
  retry_session = retry(cache_session, retries = 5, backoff_factor = 0.2)
  openmeteo = openmeteo_requests.Client(session = retry_session)

  url = "https://archive-api.open-meteo.com/v1/archive"
  params = {
    "latitude": latitude,
    "longitude": longitude,
    "start_date": start_date,
    "end_date": end_date,
    "hourly": features
  }
  responses = openmeteo.weather_api(url, params=params)
  response = responses[0]
  # Process hourly data
  hourly = response.Hourly()

  hourly_data = {"date": pd.date_range(
    start = pd.to_datetime(hourly.Time(), unit = "s", utc = True),
    end = pd.to_datetime(hourly.TimeEnd(), unit = "s", utc = True),
    freq = pd.Timedelta(seconds = hourly.Interval()),
    inclusive = "left"
  )}

  for i in range(len(features)):
    hourly_data[features[i]] = hourly.Variables(i).ValuesAsNumpy()

  hourly_dataframe = pd.DataFrame(data = hourly_data).set_index("date")

  # Save to CSV file
  hourly_dataframe.to_csv(f"openmeteo_data_{start_date}_{end_date}.csv", index = False)
  return hourly_dataframe

# Example usage
if __name__ == "__main__":
    latitude = 51.5074
    longitude = -0.1278
    start_date = "2025-09-04"
    end_date = "2025-10-04"
    features = ["temperature_2m", "relative_humidity_2m", "dew_point_2m", "apparent_temperature", "wind_speed_10m", "wind_direction_10m"]

    df = get_openmeteo_data(latitude, longitude, start_date, end_date, features)
    print(df)