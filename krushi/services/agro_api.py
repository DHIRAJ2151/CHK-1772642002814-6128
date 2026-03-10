"""
Agromonitoring API Service Layer
Handles communication with OpenWeather Agromonitoring API for crop planning
"""
import os
import requests
from datetime import datetime, timedelta
from typing import Dict, Optional, List
import logging

from django.conf import settings

logger = logging.getLogger(__name__)

# Base URL for Agromonitoring API
AGRO_BASE_URL = "https://api.agromonitoring.com/agro/1.0"


def get_api_key() -> str:
    """
    Retrieve Agromonitoring API key from environment variables.
    Raises ValueError if not configured.
    """
    api_key = os.getenv('AGROMONITORING_API_KEY') or getattr(settings, 'AGROMONITORING_API_KEY', '')
    if not api_key or api_key == 'your_agromonitoring_api_key_here':
        raise ValueError(
            "AGROMONITORING_API_KEY not configured. "
            "Please add it to your .env file. "
            "Get your free API key from: https://agromonitoring.com/api"
        )
    if isinstance(api_key, str) and (api_key.startswith('"') and api_key.endswith('"')):
        api_key = api_key.strip('"')
    if not isinstance(api_key, str) or len(api_key.strip()) < 20:
        raise ValueError(
            "AGROMONITORING_API_KEY looks invalid. "
            "Please verify your API key in .env (AGROMONITORING_API_KEY=...)."
        )
    return api_key


def create_polygon(lat: float, lon: float, name: str) -> Optional[Dict]:
    """
    Register a field polygon with Agromonitoring API.
    
    Args:
        lat: Latitude of the field center
        lon: Longitude of the field center
        name: Name identifier for the polygon
    
    Returns:
        Dictionary with polygon_id and other metadata, or None on failure
    """
    try:
        api_key = get_api_key()
        
        # Create a small square polygon around the point (approx 1km x 1km)
        # Coordinates in GeoJSON format [lon, lat]
        offset = 0.005  # roughly 500m at equator
        coordinates = [
            [lon - offset, lat - offset],
            [lon + offset, lat - offset],
            [lon + offset, lat + offset],
            [lon - offset, lat + offset],
            [lon - offset, lat - offset]  # Close the polygon
        ]
        
        payload = {
            "name": name,
            "geo_json": {
                "type": "Feature",
                "properties": {},
                "geometry": {
                    "type": "Polygon",
                    "coordinates": [coordinates]
                }
            }
        }
        
        url = f"{AGRO_BASE_URL}/polygons?appid={api_key}"
        response = requests.post(url, json=payload, timeout=30)
        response.raise_for_status()
        
        data = response.json()
        logger.info(f"Created polygon: {data.get('id')} for location ({lat}, {lon})")
        return data
        
    except requests.exceptions.RequestException as e:
        logger.error(f"Failed to create polygon: {str(e)}")
        return None
    except Exception as e:
        logger.error(f"Unexpected error creating polygon: {str(e)}")
        return None


def get_historical_weather(polygon_id: str, start_timestamp: int, end_timestamp: int) -> Optional[List[Dict]]:
    """
    Fetch historical weather data for a registered polygon.
    
    Args:
        polygon_id: ID of the registered polygon
        start_timestamp: Unix timestamp for start date
        end_timestamp: Unix timestamp for end date
    
    Returns:
        List of weather data points, or None on failure
    """
    try:
        api_key = get_api_key()
        
        url = f"{AGRO_BASE_URL}/weather/history"
        params = {
            'polyid': polygon_id,
            'start': start_timestamp,
            'end': end_timestamp,
            'appid': api_key
        }
        
        response = requests.get(url, params=params, timeout=30)
        try:
            response.raise_for_status()
        except requests.exceptions.HTTPError:
            if response.status_code in (401, 403):
                logger.error(
                    f"Agromonitoring authorization failed (HTTP {response.status_code}). "
                    f"Check AGROMONITORING_API_KEY. Response: {response.text[:500]}"
                )
            raise
        
        data = response.json()
        logger.info(f"Retrieved {len(data)} weather data points for polygon {polygon_id}")
        return data
        
    except requests.exceptions.RequestException as e:
        logger.error(f"Failed to fetch historical weather: {str(e)}")
        return None
    except Exception as e:
        logger.error(f"Unexpected error fetching weather: {str(e)}")
        return None


def delete_polygon(polygon_id: str) -> bool:
    """
    Delete a polygon from Agromonitoring (cleanup).
    
    Args:
        polygon_id: ID of the polygon to delete
    
    Returns:
        True if successful, False otherwise
    """
    try:
        api_key = get_api_key()
        
        url = f"{AGRO_BASE_URL}/polygons/{polygon_id}?appid={api_key}"
        response = requests.delete(url, timeout=30)
        response.raise_for_status()
        
        logger.info(f"Deleted polygon: {polygon_id}")
        return True
        
    except requests.exceptions.RequestException as e:
        logger.error(f"Failed to delete polygon: {str(e)}")
        return False
    except Exception as e:
        logger.error(f"Unexpected error deleting polygon: {str(e)}")
        return False


def analyze_rainfall_pattern(weather_data: List[Dict]) -> Dict:
    """
    Analyze historical weather data to identify rainfall patterns.
    
    This function processes weather data to find:
    - Weekly rainfall totals
    - Start of rainy season (first week with >20mm rainfall)
    - Average rainfall over the period
    
    Args:
        weather_data: List of weather data points from API
    
    Returns:
        Dictionary with rainfall analysis results
    """
    if not weather_data:
        return {
            'avg_rainfall': 0,
            'rainy_season_start': None,
            'weekly_rainfall': []
        }
    
    # Sort data by timestamp
    sorted_data = sorted(weather_data, key=lambda x: x.get('dt', 0))
    
    # Calculate weekly rainfall
    weekly_rainfall = []
    current_week_rain = 0
    current_week_start = None
    week_count = 0
    
    for i, data_point in enumerate(sorted_data):
        timestamp = data_point.get('dt', 0)
        date = datetime.fromtimestamp(timestamp)
        
        # Extract rainfall (rain in mm for the period)
        rain = data_point.get('rain', {})
        if isinstance(rain, dict):
            rain_mm = rain.get('1h', 0) or rain.get('3h', 0) or 0
        else:
            rain_mm = 0
        
        if current_week_start is None:
            current_week_start = date
        
        current_week_rain += rain_mm
        
        # Check if we've completed a week (7 days)
        if (date - current_week_start).days >= 7 or i == len(sorted_data) - 1:
            weekly_rainfall.append({
                'week_start': current_week_start,
                'rainfall_mm': current_week_rain
            })
            current_week_rain = 0
            current_week_start = None
            week_count += 1
    
    # Find rainy season start (first week with >20mm rainfall)
    rainy_season_start = None
    for week in weekly_rainfall:
        if week['rainfall_mm'] > 20:
            rainy_season_start = week['week_start']
            break
    
    # Calculate average rainfall
    total_rainfall = sum(week['rainfall_mm'] for week in weekly_rainfall)
    avg_rainfall = total_rainfall / len(weekly_rainfall) if weekly_rainfall else 0
    
    return {
        'avg_rainfall': round(avg_rainfall, 2),
        'rainy_season_start': rainy_season_start,
        'weekly_rainfall': weekly_rainfall,
        'total_rainfall': round(total_rainfall, 2)
    }


def estimate_soil_type(weather_data: List[Dict], lat: float, lon: float) -> str:
    """
    Estimate soil type based on location and weather patterns.
    
    This is a simplified estimation based on:
    - Rainfall patterns
    - Geographic location (latitude)
    
    Args:
        weather_data: Historical weather data
        lat: Latitude
        lon: Longitude
    
    Returns:
        Estimated soil type as string
    """
    rainfall_analysis = analyze_rainfall_pattern(weather_data)
    avg_rainfall = rainfall_analysis.get('avg_rainfall', 0)
    
    # Simple heuristic based on rainfall and latitude
    # India-specific soil type estimation
    if 8 <= lat <= 37 and 68 <= lon <= 97:  # India bounds
        if avg_rainfall > 50:
            return "Alluvial (High Rainfall)"
        elif avg_rainfall > 30:
            return "Red Soil (Moderate Rainfall)"
        elif avg_rainfall > 15:
            return "Black Soil (Semi-Arid)"
        else:
            return "Sandy/Desert Soil (Low Rainfall)"
    else:
        # Generic estimation for other regions
        if avg_rainfall > 40:
            return "Clay/Loamy (High Moisture)"
        elif avg_rainfall > 20:
            return "Loamy (Moderate Moisture)"
        else:
            return "Sandy (Low Moisture)"
