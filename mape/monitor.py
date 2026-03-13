from metamodel import *
from knowledge import *

class Monitor:
    
    def __init__(self, model_root: ModelRoot, knowledge: Knowledge):
        # Navigating the model to subscribe to all the relevant topics

        self.running = False
        self.model_root = model_root

        self.subscribers = {}

        for environment_property in model_root.environmentproperty:
            source = environment_property.source
            topic = source.topic
            print(f"Subscribing to: {topic} (as environment property source)")
            self.subscribers[topic] = source.datapath

        for interesting_property in model_root.mission.interestingproperty:
            source = interesting_property.source
            topic = source.topic
            print(f"Subscribing to: {topic} (as mission property source)")
            self.subscribers[topic] = source.datapath

        for robot in model_root.robot:
            for monitored_property in robot.monitoredrobotproperty:
                source = monitored_property.source
                topic = source.topic
                print(f"Subscribing to: {topic} (as robot property source)")
                self.subscribers[topic] = source.datapath

    def run(self):
        print("Monitor started!")
        self.running = True

    def stop(self):
        self.running = False
        print("Monitor stopped!")

    def handle_message(self, topic, data_path):
        print(f"Received message from {topic}, extracting {data_path}")