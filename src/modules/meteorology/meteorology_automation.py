import requests, datetime
import functools # Import functools for the decorator
import logging # Import logging for safe_action decorator
from modules.base_automation import BaseAutomationModule

# Decorator for safe execution and uniform error handling
def safe_action(func):
    @functools.wraps(func)
    def wrapper(*args, **kwargs):
        try:
            return func(*args, **kwargs)
        except Exception:
            logging.error(f"Error in {func.__name__}:", exc_info=True)
            return f"[FAIL] Failed to {func.__name__.replace('_', ' ')}."
    return wrapper

class MeteorologyFunctionality(BaseAutomationModule):
    def __init__(self):
        self.__base_url = "https://api.openweathermap.org"
        self.__geo_url = self.__base_url + "/geo/1.0"
        self.__data_url = self.__base_url + "/data/2.5"
        self.__api_key = "YOUR_OPENWEATHERMAP_API_KEY"
        self.__units = {"metric": "°C", "imperial": "°F", "standard": "K"}

    def _api_key(self):
        return self.__api_key
        
    def _base_url(self):
        return self.__base_url

    def _send_resquest(self, url: str, params: dict) -> dict:
        """Send a request to the REST service."""
        response = requests.get(url, params=params)
        response.raise_for_status() # Raises HTTPError for bad responses (4xx or 5xx)
        return response.json()
        
    def get_description(self) -> str:
        """Returns a brief description of the module's overall functionality."""
        return "Provides weather and air pollution data via OpenWeatherMap API."

    def get_supported_actions(self) -> dict:
        """
        Returns a dictionary where keys are action names (strings) and values
        are dictionaries containing:
        - "method_name": The name of the corresponding method in this module.
        - "description": A brief description of what the action does.
        - "example_json": An example of the JSON intent structure for this action,
                          as the LLM should generate it.
        """
        return {
            "get_current_weather": {
                "method_name": "_get_current_weather",
                "description": "Get the current weather for a location. Can specify city, lat/lon, or zip/country_code.",
                "example_json": '{"action":"get_current_weather","city":"London","units":"metric"}'
            },
            "get_forecast": {
                "method_name": "_get_forecast",
                "description": "Get a 5-day weather forecast in 3-hour intervals for a location. Can specify city, lat/lon, or zip/country_code.",
                "example_json": '{"action":"get_forecast","city":"Paris","units":"imperial"}'
            },
            "get_air_pollution": {
                "method_name": "_get_air_pollution",
                "description": "Get current air pollution data for a location. Can specify city, lat/lon, or zip/country_code.",
                "example_json": '{"action":"get_air_pollution","lat":51.5,"lon":-0.1}'
            }
        }

    def execute_function(self, name: str, args: dict):
        """Executes the specified function with the given arguments."""
        # The method_name in get_supported_actions already includes the underscore
        return getattr(self, name)(**args)
        
    def __resolve_coordinates(self, **kwargs) -> dict:
        """
        Get the geocoding information (latitude, longitude, city, country) for a given location.
        Supports lookup by lat/lon, zip code + country code, or city name (+ optional state/country code).
        Raises ValueError if insufficient information or no results are found.
        """
        if "lat" in kwargs and "lon" in kwargs:
            url = f"{self.__geo_url}/reverse"
            params = {
                "lat": kwargs["lat"],
                "lon": kwargs["lon"],
                "limit": 1,
                "appid": self.__api_key
            }
            data = self._send_resquest(url, params)
            # The /reverse endpoint returns a list of locations
            if not isinstance(data, list) or not data:
                raise ValueError("No results found for the given coordinates.")
            return {
                "lat": kwargs["lat"],
                "lon": kwargs["lon"],
                "city": data[0]["name"],
                "country": data[0]["country"]
            }

        elif "zip" in kwargs and "country_code" in kwargs:
            url = f"{self.__geo_url}/zip"
            params = {
                "zip": f"{kwargs['zip']},{kwargs['country_code']}",
                "appid": self.__api_key
            }
            data = self._send_resquest(url, params)
            # The /zip endpoint returns a single dictionary if successful
            if not isinstance(data, dict) or not data:
                raise ValueError("No results found for the given zip code and country code.")
            return {
                "lat": data["lat"],
                "lon": data["lon"],
                "city": data["name"],
                "country": data["country"]
            }

        elif "city" in kwargs:
            url = f"{self.__geo_url}/direct"
            q = kwargs["city"]
            if "state_code" in kwargs:
                q += f",{kwargs['state_code']}"
            if "country_code" in kwargs:
                q += f",{kwargs['country_code']}"
            params = {
                "q": q,
                "limit": 1,
                "appid": self.__api_key
            }
            data = self._send_resquest(url, params)
            # The /direct endpoint returns a list of locations
            if not isinstance(data, list) or not data:
                raise ValueError("No results found for the given city.")
            return {
                "lat": data[0]["lat"],
                "lon": data[0]["lon"],
                "city": data[0]["name"],
                "country": data[0]["country"]
            }

        else:
            raise ValueError("Insufficient location information. Provide lat/lon, city, or zip + country_code.")
        
    @safe_action # Apply safe_action decorator
    def _get_current_weather(self, **kwargs) -> str:
        try:
            info = self.__resolve_coordinates(**kwargs)
        except ValueError as e:
            return str(e)
        except requests.exceptions.HTTPError as e:
            return f"Error fetching weather: {e}"

        url = f"{self.__data_url}/weather"
        params = {
            "lat": info["lat"],
            "lon": info["lon"],
            "appid": self.__api_key,
            "units": kwargs.get("units", "metric"),
            "lang": kwargs.get("lang", "en")
        }

        try:
            response = self._send_resquest(url, params)
        except requests.exceptions.HTTPError as e:
            return f"Error fetching current weather data: {e}"
        
        response["city_name"] = info["city"]
        response["country"] = info["country"]
        response["units"] = kwargs.get("units", "metric")
        return self.__format_current_weather(response)
        
        
    @safe_action # Apply safe_action decorator
    def _get_forecast(self, **kwargs) -> str:
        try:
            info = self.__resolve_coordinates(**kwargs)
        except ValueError as e:
            return str(e)
        except requests.exceptions.HTTPError as e:
            return f"Error fetching forecast: {e}"

        url = f"{self.__data_url}/forecast"
        params = {
            "lat": info["lat"],
            "lon": info["lon"],
            "appid": self.__api_key,
            "units": kwargs.get("units", "metric"),
            "lang": kwargs.get("lang", "en")
        }

        try:
            response = self._send_resquest(url, params)
        except requests.exceptions.HTTPError as e:
            return f"Error fetching forecast data: {e}"

        response["city_name"] = info["city"]
        response["country"] = info["country"]
        response["units"] = kwargs.get("units", "metric")
        return self.__format_forecast(response)
        
    @safe_action # Apply safe_action decorator
    def _get_air_pollution(self, **kwargs) -> str:
        try:
            info = self.__resolve_coordinates(**kwargs)
        except ValueError as e:
            return str(e)
        except requests.exceptions.HTTPError as e:
            return f"Error fetching air pollution: {e}"

        url = f"{self.__data_url}/air_pollution"
        params = {
            "lat": info["lat"],
            "lon": info["lon"],
            "appid": self.__api_key
        }

        try:
            response = self._send_resquest(url, params)
        except requests.exceptions.HTTPError as e:
            return f"Error fetching air pollution data: {e}"

        response["city_name"] = info["city"]
        response["country"] = info["country"]
        response["units"] = kwargs.get("units", "metric") # Units not directly used for pollution, but keeping for consistency
        return self.__format_air_pollution(response)
        
    def __format_current_weather(self, response: dict):
        if not response or "weather" not in response:
            return "Sorry, I couldn't retrieve the weather data."
            
        #Location
        location = response.get("city_name")
        country = response.get("country")
        location_str = f"{location}, {country}"

        #Weather
        weather_desc = response["weather"][0].get("description").capitalize()

        #Temperatures
        temp = response["main"].get("temp", None)
        feels_like = response["main"].get("feels_like", None)
        unit = self.__units.get(response.get('units'))
        temp_str = f"{temp}{unit} (feels like {feels_like}{unit})"

        # Humidity & Pressure
        humidity = response["main"].get("humidity")
        pressure = response["main"].get("pressure")

        # Wind
        wind_speed = response.get("wind", {}).get("speed")
        wind_deg = response.get("wind", {}).get("deg")

        # Cloudiness
        clouds = response.get("clouds", {}).get("all")

        # Rain/Snow
        rain = response.get("rain", {}).get("1h")
        snow = response.get("snow", {}).get("1h")

        # Sunrise/Sunset
        sunrise = response.get("sys", {}).get("sunrise")
        sunset = response.get("sys", {}).get("sunset")
        timezone = response.get("timezone", 0)
        sunrise_time = datetime.datetime.utcfromtimestamp(sunrise + timezone).strftime('%H:%M') if sunrise else None
        sunset_time = datetime.datetime.utcfromtimestamp(sunset + timezone).strftime('%H:%M') if sunset else None

        # Build message
        report = f"Weather Report for {location_str}\n"
        report += f"- Condition: {weather_desc}\n"
        report += f"- Temperature: {temp_str}\n"
        if humidity: report += f"- Humidity: {humidity}%\n"
        if pressure: report += f"- Pressure: {pressure} hPa\n"
        if wind_speed: report += f"- Wind: {wind_speed} m/s"
        if wind_deg: report += f" from {wind_deg}°"
        report += "\n"
        if clouds is not None: report += f"- Cloudiness: {clouds}%\n"
        if rain is not None: report += f"- Rain (last 1h): {rain} mm\n"
        if snow is not None: report += f"- Snow (last 1h): {snow} mm\n"
        if sunrise_time and sunset_time:
            report += f"- Sunrise: {sunrise_time} | Sunset: {sunset_time}\n"

        return report.strip()

    def __format_forecast(self, response: dict):
        if not response or "list" not in response:
            return "Sorry, I couldn't retrieve the forecast data."
            
        #Location
        location = response.get("city_name")
        country = response.get("country")
        location_str = f"{location}, {country}"
        timezone = response.get("city", {}).get("timezone", 0)
        unit = self.__units.get(response.get('units'))

        header = f"5-Day Weather Forecast for {location_str}:\n"
        forecast_list = response["list"]

        report = ""
        for item in forecast_list:
            dt = item.get("dt")
            time_str = datetime.datetime.utcfromtimestamp(dt + timezone).strftime("%d/%m %H:%M") if dt else "Unknown time"
            weather_desc = item["weather"][0].get("description", "No description").capitalize()
            temp = item["main"].get("temp")
            report += f"- [{time_str}] {weather_desc}, {temp}{unit}\n"
            
        return header + report.strip()
        
    def __format_air_pollution(self, response: dict):
        if not response or "list" not in response:
            return "Sorry, I couldn't retrieve the air pollution data."
            
        location = response.get("city_name")
        country = response.get("country")
        location_str = f"{location}, {country}"

        data = response["list"][0]  # Assume first element for current data
        aqi = data.get("main", {}).get("aqi", "Unknown")

        pollutants = data.get("components", {})
        pollutant_strings = []
        for key, value in pollutants.items():
            pollutant_strings.append(f"- {key.upper()}: {value} µg/m³")

        aqi_meaning = {
            1: "Good",
            2: "Fair",
            3: "Moderate",
            4: "Poor",
            5: "Very Poor"
        }.get(aqi, "Unknown")

        report = f"Air Quality Report in {location_str}:\n- AQI: {aqi} ({aqi_meaning})\n" + "\n".join(pollutant_strings)

        return report.strip()
