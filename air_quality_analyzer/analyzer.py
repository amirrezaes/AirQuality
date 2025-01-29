import json
import requests
from concurrent.futures import ThreadPoolExecutor
from typing import List, Optional, Tuple, Dict


TOKEN = "f75e2f09d2fae1680d7a42a642dfdc7654392b94"
MAP_API = "https://api.waqi.info/v2/map/bounds?latlng={lat1},{lng1},{lat2},{lng2}&networks=all&token={token}"
GEO_API = "https://api.waqi.info/feed/geo:{lat};{lon}/?token={token}"

class calculate_average_pm25:
    def __init__(self, latitude_1, longitude_1, latitude_2, longitude_2, sampling_period=5, sampling_rate=1):

        self.IDLE       = 0
        self.RUNNING    = 1
        self.DONE       = 2
        self.FAILED     = 3
        self.STOPPED    = 4
        
        self.state      = self.IDLE

        self.latitude_1, self.longitude_1 = latitude_1, longitude_1
        self.latitude_2, self.longitude_2 = latitude_2, longitude_2

        self.sampling_period = sampling_period
        self.sampling_rate   = sampling_rate


    def _worker(self):
        pass


    def _extract_stations(self, json_data: dict) -> List[Tuple[float, float]] | None:
        """
        Extract all the coordinates from Map Querys Json result.
    
        Args:
            json_data (dict): JSON data containing station information
        
        Returns:
            List[Tuple[float, float]]: List of tuples containing lat, lon or None
        """

        # Check status first
        if json_data.get('status') != 'ok':
            return None
        
        coordinates = []
        for station in json_data.get('data', []):
            lat = station.get('lat')
            lon = station.get('lon')
            
            # Only add if we have both coordinates
            if lat is not None and lon is not None:
                coordinates.append((lat, lon))
        
        return coordinates
    
    
    def _extract_pm25(self, json_data: dict) -> float | None:
        """
        Extract PM2.5 value from AQI station data JSON.
        
        Args:
            json_data (dict): JSON data containing station and air quality information
            
        Returns:
            Optional[float]: PM2.5 value if found and status is ok, None otherwise
        """
        
        # Check status first
        if json_data.get('status') != 'ok':
            return None
        
        try:
            pm25_value = json_data.get('data', {}).get('iaqi', {}).get('pm25', {}).get('v')
            return float(pm25_value) if pm25_value is not None else None
        
        except (TypeError, ValueError): # In case of missing keys or invalid conversion
            return None


    def _get_map_bound(self) -> Dict | None:
        """
        Get all the stations bounded by input lat and lon using Map Query API.

        Returns:
            Dict: JSON data containing all stations within the bounds.
        """
        url = MAP_API.format(lat1=self.latitude_1, lng1=self.longitude_1, 
                             lat2=self.latitude_2, lng2=self.longitude_2,
                             token=TOKEN)

        response = requests.get(url)
        if response.status_code == 200:
            return response.json()
        else:
            return None


    def _get_station(self, lat: float, lon: float) -> Dict | None:
        """
        Get data for a specific station using its lat,lon with Geolocalized API.

        Args:
            lat (float): Latitude of the station
            lon (float): Longitude of the station
        
        Returns:
            Dict: JSON data containing station and air quality information
        """
        url = GEO_API.format(lat=lat, lon=lon, token=TOKEN)

        response = requests.get(url)
        if response.status_code == 200:
            return response.json()
        else:
            return None


    def sampling_status(self):
        return f"Sampling period: {self.sampling_period} seconds, Sampling rate: {self.sampling_rate} Hz"

    def avg_pm25_all_sites(self):
        return sum([site['pm25'] for site in self.air_quality_data]) / len(self.air_quality_data)
    
    def start_sampling(self):
        pass
    
    def stop_sampling(self):
        pass
    

        