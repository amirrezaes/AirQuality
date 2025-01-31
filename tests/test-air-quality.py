import unittest
from unittest.mock import patch, Mock
import time
import requests
from air_quality_analyzer.analyzer import calculate_average_pm25

class TestAirQualityAnalyzer(unittest.TestCase):
    def setUp(self):
        """Set up test fixtures"""
        self.analyzer = calculate_average_pm25(
            latitude_1=48,
            longitude_1=-123.377021,
            latitude_2=49.201088,
            longitude_2=-122.7613762,
            sampling_period=1,
            sampling_rate=1
        )
        self.analyzer.set_token("test_token")
        self.analyzer.set_logger_level('critical')

        # Sample API responses
        self.map_api_response = {
            "status": "ok",
            "data": [
                {"lat": 48, "lon": -123.377021},
                {"lat": 49.201088, "lon": -122.7613762}
            ]
        }
        
        self.station_api_response = {
            "status": "ok",
            "data": {
                "iaqi": {
                    "pm25": {"v": 25.0}
                }
            }
        }

    def test_initial_state(self):
        """Test initial state of the analyzer"""
        self.assertEqual(self.analyzer.state, self.analyzer.STOPPED)
        self.assertEqual(self.analyzer.pm25data, [])
        self.assertEqual(self.analyzer.sampling_status(), self.analyzer.STOPPED)

    @patch('requests.get')
    def test_state_transitions_success(self, mock_get):
        """Test state transitions for successful execution"""

        mock_get.return_value.status_code = 200
        mock_get.return_value.json.side_effect = [
            self.map_api_response,
            self.station_api_response,
            self.station_api_response
        ]

        # Start sampling (non-blocking)
        self.analyzer.start_sampling(blocking=False)
        
        # State should transition to RUNNING
        # time.sleep(0.01)  # Small delay to allow thread startup
        self.assertEqual(self.analyzer.sampling_status(), self.analyzer.RUNNING)
        
        # Wait for completion
        time.sleep(2)
        self.assertEqual(self.analyzer.sampling_status(), self.analyzer.DONE)

    @patch('requests.get')
    def test_state_transitions_failure(self, mock_get):
        """Test state transitions when API fails"""

        # Mock failed API response
        mock_get.return_value.status_code = 404
        mock_get.return_value.json.return_value = {"status": "error", "message": "Not found"}

        self.analyzer.start_sampling(blocking=True)
        self.assertEqual(self.analyzer.sampling_status(), self.analyzer.FAILED)

    def test_stop_sampling(self):
        """Test stopping the sampling process"""
        with patch('requests.get') as mock_get:
            mock_get.return_value.status_code = 200
            mock_get.return_value.json.return_value = self.map_api_response

            # Start sampling
            self.analyzer.start_sampling(blocking=False)
            time.sleep(0.1)  # Allow thread startup
            
            # Stop sampling
            self.analyzer.stop_sampling()
            self.assertEqual(self.analyzer.sampling_status(), self.analyzer.STOPPED)
            self.assertEqual(self.analyzer.pm25data, [])

    @patch('requests.get')
    def test_no_stations_found(self, mock_get):
        """Test behavior when no stations are found"""
        mock_get.return_value.status_code = 200
        mock_get.return_value.json.return_value = {"status": "ok", "data": []}

        self.analyzer.start_sampling(blocking=True)
        self.assertEqual(self.analyzer.sampling_status(), self.analyzer.DONE)

    def test_invalid_token(self):
        """Test behavior with invalid token"""
        analyzer = calculate_average_pm25(35.6892, 51.3890, 35.7272, 51.4258)
        analyzer.set_token(123)  # Invalid token type
        self.assertEqual(analyzer.sampling_status(), analyzer.FAILED)


    def test_avg_pm25_calculation(self):
        """Test PM2.5 average calculation in different states"""

        # before completion
        self.analyzer.state = self.analyzer.RUNNING
        self.assertIsNone(self.analyzer.avg_pm25_all_sites())
        
        # Test after completion
        self.analyzer.state = self.analyzer.DONE
        self.analyzer.pm25data = [25.0, 30.0, 35.0]
        self.assertEqual(self.analyzer.avg_pm25_all_sites(), 30.0)

    @patch('requests.get')
    def test_api_timeout_handling(self, mock_get):
        mock_get.side_effect = requests.exceptions.Timeout("Connection timed out")
        
        self.analyzer.start_sampling(blocking=True)
        self.assertEqual(self.analyzer.sampling_status(), self.analyzer.FAILED)

    def test_state_consistency(self):
        """Test state consistency across multiple stops and starts"""
        with patch('requests.get') as mock_get:
            mock_get.return_value.status_code = 200
            mock_get.return_value.json.return_value = self.map_api_response
            
            # Start and stop multiple times
            self.analyzer.start_sampling(blocking=False)
            time.sleep(0.1)
            self.analyzer.stop_sampling()
            self.assertEqual(self.analyzer.sampling_status(), self.analyzer.STOPPED)
            
            self.analyzer.start_sampling(blocking=False)
            time.sleep(0.1)
            self.analyzer.stop_sampling()
            self.assertEqual(self.analyzer.sampling_status(), self.analyzer.STOPPED)

if __name__ == '__main__':
    unittest.main()
