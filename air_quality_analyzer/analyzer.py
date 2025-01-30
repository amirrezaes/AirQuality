import json
import requests
from threading import Thread, Timer, active_count
from concurrent.futures import ThreadPoolExecutor, as_completed
from typing import List, Optional, Tuple, Dict



MAP_API = "https://api.waqi.info/v2/map/bounds?latlng={lat1},{lng1},{lat2},{lng2}&networks=all&token={token}"
GEO_API = "https://api.waqi.info/feed/geo:{lat};{lon}/?token={token}"

class calculate_average_pm25:
    def __init__(self, latitude_1, longitude_1, latitude_2, longitude_2, sampling_period=5, sampling_rate=1):

        self.TOKEN = ""

        self.IDLE       = 'IDLE'
        self.RUNNING    = 'RUNNING'
        self.DONE       = 'DONE'
        self.FAILED     = 'FAILED'
        self.STOPPED    = 'STOPPED'
        
        self.state      = self.STOPPED

        self.latitude_1, self.longitude_1 = latitude_1, longitude_1
        self.latitude_2, self.longitude_2 = latitude_2, longitude_2
        

        self.__sampling_period = sampling_period
        self.__sampling_rate   = sampling_rate

        self.__stations = [] # holds station coordinates
        self.pm25data   = []

        self.__worker_threads = []
        self.thread_cnt       = 8 # can be adjusted for performance
        


    
    def __handle_api_error(self, error: dict) -> None:
        """
        Handle API errors and print the message.
        
        Args:
            error (dict): JSON data containing error message
        """
        print(f"Error: {error.get('message')}")


    def __extract_stations(self, json_data: dict) -> List[Tuple[float, float]] | None:
        """
        Extract all the coordinates from Map Querys Json result.
    
        Args:
            json_data (dict): JSON data containing station information
        
        Returns:
            List[Tuple[float, float]]: List of tuples containing lat, lon or None
        """

        # Check status first
        if json_data.get('status') != 'ok':
            self._handle_api_error(json_data)
            return None
        

        coordinates = []
        for station in json_data.get('data', []):
            lat = station.get('lat')
            lon = station.get('lon')
            
            # Only add if we have both coordinates
            if lat is not None and lon is not None:
                coordinates.append((lat, lon))
        
        return coordinates
    
    
    def __extract_pm25(self, json_data: dict) -> float | None:
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


    def __get_map_bound(self) -> Dict | None:
        """
        Get all the stations bounded by input lat and lon using Map Query API.

        Returns:
            Dict: JSON data containing all stations within the bounds.
        """
        url = MAP_API.format(lat1=self.latitude_1, lng1=self.longitude_1, 
                             lat2=self.latitude_2, lng2=self.longitude_2,
                             token=self.TOKEN)

        response = requests.get(url)
        if response.status_code == 200:
            return response.json()
        else:
            return None


    def __get_station(self, lat: float, lon: float) -> Dict | None:
        """
        Get data for a specific station using its lat,lon with Geolocalized API.

        Args:
            lat (float): Latitude of the station
            lon (float): Longitude of the station
        
        Returns:
            Dict: JSON data containing station and air quality information
        """
        url = GEO_API.format(lat=lat, lon=lon, token=self.TOKEN)

        response = requests.get(url)
        if response.status_code == 200:
            return response.json()
        else:
            return None
    
    
    def __get_pm25(self, station: Tuple[float, float]) -> Optional[float]:
        """
        Get PM2.5 value for a specific station.

        Args:
            station (Tuple[float, float]): Tuple containing lat, lon of the station

        Returns:
            Optional[float]: PM2.5 value if found, None otherwise
        """
        station_data = self.__get_station(*station)
        pm25_val = self.__extract_pm25(station_data)
        return pm25_val

    def __worker(self):
        '''
        Run multiple threads to get PM2.5 values for all stations.
        '''
        results = []
        with ThreadPoolExecutor(max_workers=self.thread_cnt) as executor:
            thread_dict = {executor.submit(self.__get_pm25, st): st for st in self.__stations}

            for thread in as_completed(thread_dict):
                station = thread_dict[thread]

                try:
                    pm25_val = thread.result()
                    if pm25_val is not None:
                        results.append(pm25_val)

                except Exception as exc:
                    print(f'{station} generated an exception: {exc}')
    
    def _worker_thread_wrapper(self):
        '''
        Wrapper function to run the worker function in a thread.
        '''
        work_thread = Thread(target=self.__worker)
        work_thread.start()


    def start_sampling(self):
        if self.TOKEN: # check if token is set
            if self.__stations == []: # if stations are not already extracted
                self.__stations = self.__extract_stations(self.__get_map_bound())
        else:
            print("Error: Token not set. use set_token()")
            self.state = self.FAILED
            return
        
        self.state = self.RUNNING

        for delay in range(0, self.__sampling_period * 60, 60 // self.__sampling_rate):
            
            # Non-blocking timers to run worker threads at sampling rate
            self.__worker_threads.append(Timer(delay , self._worker_thread_wrapper))
            self.__worker_threads[-1].start()
        
    
    def stop_sampling(self):
        pass


    def sampling_status(self):
        if active_count() == 1:
            self.state = self.DONE
        return f"worker threads: {len(self.__worker_threads)} | state: {self.state}"


    def avg_pm25_all_sites(self):
        pass
    
    def set_token(self, token):
        self.TOKEN = token

    

        