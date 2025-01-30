import json
import requests
from threading import Thread, Timer, active_count, Lock, current_thread
from concurrent.futures import ThreadPoolExecutor, as_completed
from typing import List, Optional, Tuple, Dict
import logging

logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(name)s - %(levelname)s - %(message)s')


# API URLs
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

        self.__sampling_threads = {}
        self.__lock = Lock()
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
            self.__handle_api_error(json_data)
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

    def __set_state(self, thread_state: str, thread_obj: Thread):
        '''
        Set the state of each thread and update the object state with thread safety.
        '''
        with self.__lock:
            self.__sampling_threads[thread_obj] = thread_state

            logging.info(f"{thread_obj.name} state: {thread_state}")

            if any([state == self.RUNNING for state in self.__sampling_threads.values()]):
                self.state = self.RUNNING

            elif all([state == self.DONE for state in self.__sampling_threads.values()]):
                self.state = self.DONE

            elif all([state == self.FAILED for state in self.__sampling_threads.values()]):
                self.state = self.FAILED

            else:
                self.state = self.IDLE
            
            logging.info(f"State: {self.state}")
            

    def __smapler(self):
        '''
        Run multiple threads to get PM2.5 values for all stations.
        '''
        results = []
        self.__set_state(self.RUNNING , current_thread())

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

        self.__set_state(self.DONE, current_thread())
    
    def __smapler_thread_wrapper(self, name="Worker"):
        '''
        Wrapper function to run the worker function in a thread.
        '''
        work_thread = Thread(target=self.__smapler, name=name)
        work_thread.start()


    def start_sampling(self) -> None:
        '''
        Start sampling PM2.5 values for all stations.
        '''

        if self.TOKEN: # check if token is set
            if self.__stations == []: # if stations are not already extracted
                self.__stations = self.__extract_stations(self.__get_map_bound())
        else:
            print("Error: Token not set. use set_token()")
            self.state = self.FAILED
            return


        for delay in range(0, self.__sampling_period * 60, 60 // self.__sampling_rate):
            # Non-blocking timers threads to run worker threads on sampling intervals
            sampling_thread = Timer(delay, 
                                    self.__smapler_thread_wrapper, args=[f"Sampler-{delay}s"]
                                    )
            self.__sampling_threads[sampling_thread] = self.IDLE
            sampling_thread.start()
        
    
    def stop_sampling(self) -> None:
        '''
        Stop the sampling process. Clean up data.
        '''
        # wait for running threads to finish and cancel the rest
        for thread,state in self.__sampling_threads.items():
            if state == self.RUNNING:
                thread.join()
            elif state == self.IDLE:
                self.__sampling_threads[thread] = self.STOPPED
                thread.cancel()

        self.state = self.STOPPED

        # clean up for next run
        self.pm25data.clear()
        self.__sampling_threads.clear()
        


    def sampling_status(self) -> str:
        '''
        Get the status of the sampling process.

        Returns:
            str: Status of the sampling process
        '''
        return self.state


    def avg_pm25_all_sites(self) -> float:
        pass
    
    def set_token(self, token: str) -> None:
        '''
        Set the token for the API.

        Args:
            token (str): API token for the waqi.info API.
        '''
        if isinstance(token, str):
            self.TOKEN = token
        else:
            print("Error: Token must be a string.")
            self.state = self.FAILED
            return

    

        