#!/usr/bin/env python3

class Monitor:
    """Monitor component for the MAPE loop.

    Placeholder empty class.
    """
    pass

# Test

import sys, pika, json, subprocess
sys.path.append('../../../functions/turtlebot-DT/')
from get_credentials import get_data
from mission_utils import get_distances, parse_mission_mproperties, calculate_ave_speed, find_alternative_plan
sys.path.append('../../../models/turtlebot-DT/')
from build_model import store_data
from battery_model import predict_battery_level, intersect
from basic_motion_model import estimate_mission_remaining_time
from datetime import datetime

mission_metamodel_path = '../../../data/turtlebot-DT/test.json'
mission_instance_path = '../../../data/turtlebot-DT/mission.json'
with open(mission_instance_path, 'r') as file:
    mission_instance = json.load(file)

minimum_speed = 0.15
analyzing = False #if the DT is already analyzing do not trigger a new round | what should the monitor do while the system is analyzing?

#Set up the connection to the rabbitMQ server
login_info = get_data()
if "username" in login_info:
    username = login_info["username"]
else: 
    print("Username should be provided in the credentials json file")
    sys.exit()
if "password" in login_info:
    password = login_info["password"]
else: 
    print("Password should be provided in the credentials json file")
    sys.exit()
if "hostname" in login_info:
    hostname = login_info["hostname"]
else: 
    print("Hostname should be provided in the credentials json file")
    sys.exit()
if "vhost" in login_info:
    vhost = login_info["vhost"]
else: 
    print("Vhost should be provided in the credentials json file")
    sys.exit()
if "port" in login_info:
    port = login_info["port"]
else: 
    print("port should be provided in the credentials json file")
    sys.exit()

#Create connection to rabbitMQ server
credentials = pika.PlainCredentials(username, password)
print("Creating connection to the rabbitMQ server")
connection = pika.BlockingConnection(pika.ConnectionParameters(hostname, port, vhost, credentials=credentials))

channel = connection.channel()
print("Creating a channel")

print("Declaring exchange")
channel.exchange_declare(exchange='tb-test', exchange_type='direct')

print("Creating queue")
result = channel.queue_declare(queue='', exclusive=True)
queue_name = result.method.queue

channel.queue_bind(exchange='tb-test', queue=queue_name,
                   routing_key='data.from_tb')

def monitor(properties):
    if properties: 
        print(f"[DT-INFO] Monitoring {properties}")
        for p in properties:
            print(f"[DT-INFO] Evaluate expression {p[1]} for property {p[0]} ")
            if eval(p[1]):
                print("[DT-INFO] All good")
            else:
                print("[DT-ALARM] Robot will reach end of battery before the mission is complete")
                return False
    return True

def predict(message):
    global mission_instance

    print('RUNNING PREDICTION')
    task = int(message["task_data"])
    time = message["time"]
    # Predict future values and check if they are ok

    # Retrieve average speed
    ave_speed = calculate_ave_speed() #using default time_window = 10, i.e., average 10 data points if available
    print(f'Computed average speed: {ave_speed}')

    # Get distances for preferred mission
    distances = get_distances(mission_instance, task)
    print(f'Computed distances: {distances}')

    # Check the estimating remaining time to complete the mission and use it as time_window
    time_window = estimate_mission_remaining_time(distances, ave_speed)
    print(f'Estimated mission remaining time: {time_window}')

    epoch_time = int(datetime.fromisoformat(time).timestamp())
    to_monitor = []
    p_theta = -1 # TODO A better solution is needed here, if there are more than 1 parameters
    for p in monitored_properties:
        if "/battery" in p[0]: # TODO This topic should be parametrized
            print(f"[DT-INFO] Predicting battery value at epoch {epoch_time + time_window}")
            predicted_battery_level = predict_battery_level(epoch_time, time_window)
            expression = str(predicted_battery_level) + p[1]
            to_monitor.append([p[0],expression])
            p_theta = p[2]
    result = monitor(to_monitor)
    if not result:
        # Find time left, by calculating the intersection between the threshold and prediction segments, 
        # starting at current_time with end at current_time + time_window
        threshold_start = (0, p_theta)
        threshold_end = (time_window, p_theta)
        pbl = predict_battery_level(epoch_time, 1) # Predict one second ahead, to get two points and
        b_predict_start = (0, pbl)
        b_predict_end = (time_window, predicted_battery_level)
        inter = intersect(threshold_start, threshold_end, b_predict_start, b_predict_end)
        if not inter:
            time_left = 0
        else:
            time_left = inter[0] # The time is the x coordinate of the intersection point

        # Look for an alternate plan that is feasible
        alternative = find_alternative_plan(mission_instance, ave_speed, task, time_left)

        # If no alternate plan found tell robot to go home
        if not alternative:
            msg = {'new_plan.data': "GOHOME"} # The slash before the topic is added at the rmq_bridge
            channel.basic_publish(exchange='tb-test',
                routing_key='data.to_tb',
                body=json.dumps(msg))

        else: # Send to the robot the alternate plan
            tasks = ''
            for t in alternative:
                tasks = tasks + ' ' + str(t)

            msg = {'new_plan.data': tasks} # The slash before the topic is added at the rmq_bridge
            channel.basic_publish(exchange='tb-test',
                routing_key='data.to_tb',
                body=json.dumps(msg))
    else:
        msg = {'new_plan.data': "OK"}
        channel.basic_publish(exchange='tb-test',
            routing_key='data.to_tb',
            body=json.dumps(msg))

def parse_message(message):
    mproperties_data_point = []
    for element in message:
        for p in monitored_properties:
            temp = p[0]
            temp = temp[1:] # TODO this is to remove the slash.... needs to be fixed to something less adhoc-y
            if temp in element or element in temp:
                expression = str(message[element]) + p[1]
                mproperties_data_point.append([p[0], expression])
    return mproperties_data_point

def talk_to_robot(field, data):

    msg = {field: data} # The slash before the topic is added at the rmq_bridge
    channel.basic_publish(exchange='tb-test',
                routing_key='data.to_tb',
                body=json.dumps(data))


def callback(ch, method, properties, body):
    print("Received [x] %r" % body)
    message = json.loads(body)
    property_data = parse_message(message)
    # Predict only when a task message is received
    if "task_data" in message.keys():
        if "Mission_end" in message["task_data"]:
            print(f"[DT-Info] Mission complete")
            sys.exit()
        predict(message)
    else: # Else, check current value, and then store the data (commented for now: just store data)
        property_data = parse_message(message)
        # if not monitor(property_data):
        #    print(f"[DT-Alarm] PT Dying - DT out")
        #    sys.exit()
        store_data(message)
        #pass

monitored_properties = parse_mission_mproperties(mission_metamodel_path)

print('[DT-INFO] I am consuming the commands sent from the TB')
print('[DT-INFO] Monitoring the following properties ', monitored_properties)

channel.basic_consume(
    queue=queue_name, on_message_callback=callback, auto_ack=True)

channel.start_consuming()

connection.close()
