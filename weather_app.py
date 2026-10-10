import json
import math
from typing import Any
from urllib.error import HTTPError, URLError
from urllib.parse import urlencode
from urllib.request import urlopen

from flask import Flask, render_template, request


MAX_CITY_LENGTH = 100
API_TIMEOUT_SECONDS = 8
GEOCODING_URL = "https://geocoding-api.open-meteo.com/v1/search"
FORECAST_URL = "https://api.open-meteo.com/v1/forecast"

app = Flask(__name__)


class WeatherServiceError(Exception):
    pass


def _fetch_json(url: str) -> dict[str, Any]:
    try:
        with urlopen(url, timeout=API_TIMEOUT_SECONDS) as response:
            data = json.load(response)
    except (HTTPError, URLError, TimeoutError, json.JSONDecodeError) as error:
        raise WeatherServiceError(
            "The weather service is temporarily unavailable. Please try again."
        ) from error

    if not isinstance(data, dict):
        raise WeatherServiceError("The weather service returned an invalid response.")
    return data


def _get_weather(city: str) -> dict[str, Any] | None:
    location_query = urlencode({"name": city, "count": 1, "language": "en", "format": "json"})
    locations = _fetch_json(f"{GEOCODING_URL}?{location_query}").get("results")
    if not locations:
        return None
    if not isinstance(locations, list) or not isinstance(locations[0], dict):
        raise WeatherServiceError("The weather service returned an invalid location.")

    location = locations[0]
    latitude = location.get("latitude")
    longitude = location.get("longitude")
    if not isinstance(latitude, (int, float)) or not isinstance(longitude, (int, float)):
        raise WeatherServiceError("The weather service returned an invalid location.")

    forecast_query = urlencode(
        {
            "latitude": latitude,
            "longitude": longitude,
            "current": (
                "temperature_2m,relative_humidity_2m,apparent_temperature,"
                "is_day,precipitation,weather_code,wind_speed_10m"
            ),
            "timezone": "auto",
        }
    )
    current = _fetch_json(f"{FORECAST_URL}?{forecast_query}").get("current")
    if not isinstance(current, dict):
        raise WeatherServiceError("The weather service returned incomplete weather data.")

    code = current.get("weather_code")
    is_day = current.get("is_day")
    temperature = current.get("temperature_2m")
    if not isinstance(code, int) or not isinstance(is_day, int):
        raise WeatherServiceError("The weather service returned incomplete weather data.")
    if not isinstance(temperature, (int, float)) or not math.isfinite(temperature):
        raise WeatherServiceError("The weather service returned incomplete weather data.")

    description, icon = _condition_for_code(code, bool(is_day))
    return {
        "city": location.get("name", city),
        "region": location.get("admin1"),
        "country": location.get("country"),
        "temperature": round(temperature),
        "description": description,
        "icon": icon,
        "humidity": current.get("relative_humidity_2m"),
        "feels_like": current.get("apparent_temperature"),
        "wind_speed": current.get("wind_speed_10m"),
        "precipitation": current.get("precipitation"),
    }


def _condition_for_code(code: int, is_day: bool) -> tuple[str, str]:
    conditions = {
        0: ("Clear sky", "☀️" if is_day else "🌙"),
        1: ("Mainly clear", "🌤️" if is_day else "🌙"),
        2: ("Partly cloudy", "⛅"),
        3: ("Overcast", "☁️"),
        45: ("Fog", "🌫️"),
        48: ("Depositing rime fog", "🌫️"),
        51: ("Light drizzle", "🌦️"),
        53: ("Moderate drizzle", "🌦️"),
        55: ("Dense drizzle", "🌧️"),
        56: ("Light freezing drizzle", "🌧️"),
        57: ("Dense freezing drizzle", "🌧️"),
        61: ("Slight rain", "🌧️"),
        63: ("Moderate rain", "🌧️"),
        65: ("Heavy rain", "🌧️"),
        66: ("Light freezing rain", "🌧️"),
        67: ("Heavy freezing rain", "🌧️"),
        71: ("Slight snow", "🌨️"),
        73: ("Moderate snow", "🌨️"),
        75: ("Heavy snow", "❄️"),
        77: ("Snow grains", "🌨️"),
        80: ("Slight rain showers", "🌦️"),
        81: ("Moderate rain showers", "🌧️"),
        82: ("Violent rain showers", "⛈️"),
        85: ("Slight snow showers", "🌨️"),
        86: ("Heavy snow showers", "❄️"),
        95: ("Thunderstorm", "⛈️"),
        96: ("Thunderstorm with slight hail", "⛈️"),
        99: ("Thunderstorm with heavy hail", "⛈️"),
    }
    return conditions.get(code, ("Weather conditions", "🌡️"))


@app.get("/")
def home() -> str:
    city = request.args.get("city", "").strip()
    error = None
    weather = None

    if len(city) > MAX_CITY_LENGTH:
        error = f"City names must be {MAX_CITY_LENGTH} characters or fewer."
    elif city:
        try:
            weather = _get_weather(city)
            if weather is None:
                error = f"We couldn't find “{city}”. Check the spelling and try again."
        except WeatherServiceError as service_error:
            error = str(service_error)

    return render_template("weather.html", city=city, weather=weather, error=error)


if __name__ == "__main__":
    app.run()
