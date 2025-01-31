from air_quality_analyzer.analyzer import calculate_average_pm25
import time

my_obj = calculate_average_pm25(48.441591, -123.377021, 49.201088, -122.7613762, 1, 5)

my_obj.set_token("f75e2f09d2fae1680d7a42a642dfdc7654392b94")

my_obj.start_sampling()

run = True
while run:
    inp = input("Press 'q' to quit: ")
    if inp == 'q':
        run = False
        my_obj.stop_sampling()
        break


print(my_obj.sampling_status())
print(my_obj.avg_pm25_all_sites())