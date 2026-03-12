# Wraps the MAPE-K, reads and stores the model, the M, A, P, E components, the knowledge (?)

from monitor import Monitor
from analyze import Analyze
from plan import Plan
from execute import Execute
from tb_simulator import TBSimulation
from flask import Flask, request, jsonify
import sys, os
sys.path.append('../../../functions/turtlebot-DT/')
from get_credentials import get_data
import pika
import ssl
import json
import signal
import threading

from model_reader import read_model
from knowledge import *
# Wraps the MAPE-K, reads and stores the model, the M, A, P, E components, the knowledge (?)

class DigitalTwin:

    def __init__(self):

        self.knowledge = Knowledge()

    def init_dt(self, model_path: str):
        # Read model
        self.model_root = read_model(model_path)

        # Instantiate DT components
        self.monitor = Monitor(self.model_root, self.knowledge)
        # self.analyze = Analyze(self.model_root)
        # self.plan = Plan(self.model_root)
        # self.execute = Execute(self.model_root)
        self.simulation = TBSimulation() # <- this is domain-dependent

    def run(self):
        self.monitor.run()

    def stop(self):
        self.monitor.stop()

    def inner_evolve(self):
        ### Changes inside the simulation component
        pass

    def outer_evolve(self, model):
        self.monitor.update_model(model)
        # self.analyze.update_model(model)
        # self.plan.update_model(model)

    def consume(self, message):
        print(f"DT: Received message #{self.message_counter}")


app = Flask(__name__)
_dt = DigitalTwin()
dt_lock = threading.RLock()

def setup_rabbitmq():
    # Setup pika connection
    login_info = get_data()
    if "username" in login_info:
        username = login_info["username"]
        print(username)
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
    ssl_ca_cert: str = os.getenv('RABBITMQ_SSL_CA_CERT', '')
    context = ssl.create_default_context(cafile=ssl_ca_cert)
    ssl_options = pika.SSLOptions(context)
    connection = pika.BlockingConnection(pika.ConnectionParameters(hostname, port, vhost, credentials=credentials, ssl_options=ssl_options))

    channel = connection.channel()
    print("Creating a channel")

    print("Declaring exchange")
    channel.exchange_declare(exchange='tb-test', exchange_type='direct')

    # Start the subscription to the data sources

    print("Creating queue")
    result = channel.queue_declare(queue='', exclusive=True)
    queue_name = result.method.queue

    channel.queue_bind(exchange='tb-test', queue=queue_name, routing_key='data.from_tb')
    return connection, channel, queue_name

@app.route("/run", methods=["GET"])
def run_endpoint():
    with dt_lock:
        _dt.run()
    return jsonify({"status": "ok", "action": "run"})

@app.route("/stop", methods=["GET"])
def stop_endpoint():
    with dt_lock:
        _dt.stop()
    return jsonify({"status": "ok", "action": "stop"})

@app.route("/inner_evolve", methods=["GET"])
def inner_evolve_endpoint():
    with dt_lock:
        _dt.inner_evolve()
    return jsonify({"status": "ok", "action": "inner_evolve"})

@app.route("/outer_evolve", methods=["GET"])
def outer_evolve_endpoint():
    model = request.args.get("model")
    if model is None:
        return jsonify({"status": "error", "message": "missing required query param 'model'"}), 400
    with dt_lock:
        _dt.outer_evolve(model)
    return jsonify({"status": "ok", "action": "outer_evolve", "model": model})

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

def start_consumer(stop_event, _dt):
    connection, channel, queue_name = setup_rabbitmq()
    channel.basic_qos(prefetch_count=1)

    def callback(ch, method, properties, body):
        # print("Received %r" % body)
        message = json.loads(body)
        print(f"Message: {message}")

        try:
            with dt_lock:
                _dt.consume(message)
            ch.basic_ack(delivery_tag=method.delivery_tag)
        except Exception as e:
            print(f"Callback error: {e}")
            ch.basic_nack(delivery_tag=method.delivery_tag, requeue=True)

    print("Starting consuming messages")
    channel.basic_consume(
        queue=queue_name,
        on_message_callback=callback,
        auto_ack=False
    )

    try:
        while not stop_event.is_set():
            connection.process_data_events(time_limit=1)
    finally:
        try:
            connection.close()
        except Exception:
            pass


if __name__ == "__main__":
    model_path = sys.argv[1]
    _dt.init_dt(model_path)

    stop_event = threading.Event()

    t = threading.Thread(
        target=start_consumer,
        args=(stop_event, _dt),
        daemon=True
    )
    t.start()

    def handle_shutdown(signum, frame):
        print("Shutting down...")
        stop_event.set()
        t.join(timeout=5)
        sys.exit(0)

    signal.signal(signal.SIGINT, handle_shutdown)
    signal.signal(signal.SIGTERM, handle_shutdown)

    app.run(host="0.0.0.0", port=5000, debug=False, use_reloader=False)