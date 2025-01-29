from air_quality_analyzer.analyzer import calculate_average_pm25

a = calculate_average_pm25(48.441591, -123.377021, 49.201088, -122.7613762)
b = a._get_station(49.1414, -123.1083)
c = a._extract_pm25(b)
print(c)