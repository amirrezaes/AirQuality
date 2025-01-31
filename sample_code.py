from air_quality_analyzer.analyzer import calculate_average_pm25
import time

my_obj = calculate_average_pm25(48, -123.377021, 49.201088, -122.7613762, 1, 5) # victoria to vancouver

my_obj.set_token("f75e2f09d2fae1680d7a42a642dfdc7654392b94")


# Running in non-blocking fashion

my_obj.start_sampling()

run = True
while run:
    time.sleep(10)
    print("sampling status: ", my_obj.sampling_status())
    if my_obj.sampling_status() == my_obj.DONE:
        run = False

print("sampling status: ", my_obj.sampling_status())
print("pm25 avg:", my_obj.avg_pm25_all_sites())

# running in blocking fashion
my_obj.start_sampling(blocking=True)
print("this message should not be printed until sampling is done")
print("sampling status: ", my_obj.sampling_status())
print("pm25 avg:", my_obj.avg_pm25_all_sites())