import requests
from threading import Thread, Timer, Lock, current_thread, active_count
from concurrent.futures import ThreadPoolExecutor, as_completed
from typing import List, Optional, Tuple, Dict
import logging

logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')


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
        self._thread_timeout   = sampling_period * 60 + 5 # 5 seconds extra if needed

        self.__stations = [] # holds station coordinates
        self.pm25data   = []

        self.__timer_threads = {}
        self.__sampling_threads = {}
        self.__lock = Lock()
        self.thread_cnt       = 8 # can be adjusted for performance
        


    
    def __handle_api_error(self, error: dict) -> None:
        """
        Handle API errors and print the message.
        
        Args:
            error (dict): JSON data containing error message
        """
        logging.error(f"{error.get('message')}")

    def __calculate_avg_pm25(self) -> float:
        """
        Calculate the average PM2.5 value from the data.

        Returns:
            float: Average PM2.5 value
        """
        if self.pm25data == []:
            return 0

        return sum(self.pm25data) / len(self.pm25data)

    def __extract_stations(self, json_data: dict) -> List[Tuple[float, float]] | None:
        """
        Extract all the coordinates from Map Query's Json result.
    
        Args:
            json_data (dict): JSON data containing station information
        
        Returns:
            List[Tuple[float, float]]: List of tuples containing lat, lon or None
        """
        if json_data is None: # In case of failed request
            return None

        # Check status first
        if json_data.get('status') != 'ok':
            self.__handle_api_error(json_data)
            return None
        

        coordinates = []
        try:
            for station in json_data.get('data', []):
                lat = station.get('lat')
                lon = station.get('lon')
                
                # Only add if we have both coordinates
                if lat is not None and lon is not None:
                    coordinates.append((lat, lon))
        except (TypeError, ValueError): # In case of missing keys or invalid conversion
            return None
        
        return coordinates
    
    
    def __extract_pm25(self, json_data: dict) -> float | None:
        """
        Extract PM2.5 value from AQI station data JSON.
        
        Args:
            json_data (dict): JSON data containing station and air quality information
            
        Returns:
            Optional[float]: PM2.5 value if found and status is ok, None otherwise
        """
        if json_data is None: # In case of failed request
            return None
        
        # Check status first
        if json_data.get('status') != 'ok':
            self.__handle_api_error(json_data)
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

        try:
            response = requests.get(url)
            if response.status_code == 200:
                return response.json()
            else:
                return None
        except requests.exceptions.RequestException as e:
            logging.error(f"{e}")
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

        try:
            response = requests.get(url)
            if response.status_code == 200:
                return response.json()
            else:
                return None
        except requests.exceptions.RequestException as e:
            logging.error(f"{e}")
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
            timer_object = self.__sampling_threads[thread_obj] # get parent timer thread object
            self.__timer_threads[timer_object] = thread_state # update timer thread state

            logging.info(f"{thread_obj.name} state: {self.__timer_threads[timer_object]}")

            if any([state == self.RUNNING for state in self.__timer_threads.values()]):
                self.state = self.RUNNING

            elif all([state == self.DONE for state in self.__timer_threads.values()]):
                self.state = self.DONE

            elif all([state == self.FAILED for state in self.__timer_threads.values()]):
                self.state = self.FAILED

            else:
                self.state = self.IDLE
            
            

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
                    if pm25_val is not None: # ignore failed requests
                        results.append(pm25_val)

                except Exception as exc:
                    logging.error(f"station at lat,lng {station} generated Error: {exc}")


        
        if results:
            with self.__lock:
                self.pm25data.extend(results)
            self.__set_state(self.DONE, current_thread())
        else:
            self.__set_state(self.FAILED, current_thread())

    
    def __smapler_thread_wrapper(self, name="Worker", blocking=False):
        '''
        Wrapper function to run the worker function in a thread.
        '''
        work_thread = Thread(target=self.__smapler, name=name)

        with self.__lock:
            self.__sampling_threads[work_thread] = current_thread() # parent timer thread as value

        work_thread.start()

        if blocking:
            work_thread.join(timeout=self._thread_timeout)


    def start_sampling(self, blocking=False) -> None:
        '''
        Start sampling PM2.5 values with multiple threads.

        Args:
            blocking (bool): If True, the function will block until all threads are finished.
        '''

        if not self.TOKEN: # if token is not set
            logging.error("Error: Token is not set.")
            self.state = self.FAILED
            return

        if self.__stations == []: # if stations are not already extracted
            self.__stations = self.__extract_stations(self.__get_map_bound())

            if self.__stations is None:
                logging.error("Request to get stations failed.")
                self.state = self.FAILED
                return

            elif self.__stations == []:
                logging.error("No stations found in the given bounds.")
                self.state = self.DONE
                return


        for delay in range(0, self.__sampling_period * 60, 60 // self.__sampling_rate):
            # Non-blocking timers threads to run worker threads on sampling intervals
            timer_thread = Timer(delay, 
                                    self.__smapler_thread_wrapper, 
                                    args=[f"Sampler-{delay}s", blocking],
                                    )
            timer_thread.setName(f"Timer-{delay}s")
            self.__timer_threads[timer_thread] = self.IDLE
            
        
        for thread in self.__timer_threads.keys():
            thread.start()

        if blocking:
            for thread in self.__timer_threads.keys():
                thread.join()


                
        
    
    def stop_sampling(self) -> None:
        '''
        Stop the sampling process. Clean up data.
        '''

        # wait for running sampling thread to finish
        for sthread in self.__sampling_threads:
            if sthread.is_alive():
                logging.info(f"Waiting for {sthread.name} to finish.")
                sthread.join()

        # wait for Running Timer threads to finish and cancel the rest
        for thread,state in self.__timer_threads.items():
            if state == self.RUNNING:
                logging.info(f"Waiting for {thread.name} to finish.")
                thread.join()
            elif state == self.IDLE or thread.is_alive():
                self.__timer_threads[thread] = self.STOPPED
                thread.cancel()

        self.state = self.STOPPED

        logging.info("Sampling stopped.")

        # clean up for next run
        self.pm25data.clear()
        self.__timer_threads.clear()
        self.__sampling_threads.clear()
        


    def sampling_status(self) -> str:
        '''
        Get the status of the sampling process.

        Returns:
            str: Status of the sampling process
        '''
        return self.state


    def avg_pm25_all_sites(self) -> float | None:
        '''
        Get the average PM2.5 value from all the sites if the sampling is done.

        Returns:
            float: Average PM2.5 value
        '''

        if self.state == self.DONE:
                return self.__calculate_avg_pm25()
        else:
            return None
        
    
    def set_token(self, token: str) -> None:
        '''
        Set the token for the API.

        Args:
            token (str): API token for the waqi.info API.
        '''
        if isinstance(token, str):
            self.TOKEN = token
        else:
            logging.error("Token must be a string.")
            self.state = self.FAILED
            return
