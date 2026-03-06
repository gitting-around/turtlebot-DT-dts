# Wraps the MAPE-K, reads and stores the model, the M, A, P, E components, the knowledge (?)

from .monitor import Monitor
from .analyze import Analyze
from .plan import Plan
from .execute import Execute
from .tb_simulator import TBSimulation
from flask import Flask, request, jsonify

# Wraps the MAPE-K, reads and stores the model, the M, A, P, E components, the knowledge (?)

class DigitalTwin:

    def __init__(self):
        self.monitor = Monitor()
        self.analyze = Analyze()
        self.plan = Plan()
        self.execute = Execute()

        self.simulation = TBSimulation() # <- this is domain-dependent

        # Setup pika connection

    def run(self):
        self.monitor.run()

    def inner_evolve(self):
        ### Changes inside the simulation component
        pass

    def outer_evolve(self, model):
        self.monitor.update_model(model)
        self.analyze.update_model(model)
        self.plan.update_model(model)


app = Flask(__name__)

# single DigitalTwin instance used by the endpoints
_dt = DigitalTwin()


@app.route("/run", methods=["GET"])
def run_endpoint():
    _dt.run()
    return jsonify({"status": "ok", "action": "run"})


@app.route("/inner_evolve", methods=["GET"])
def inner_evolve_endpoint():
    _dt.inner_evolve()
    return jsonify({"status": "ok", "action": "inner_evolve"})


@app.route("/outer_evolve", methods=["GET"])
def outer_evolve_endpoint():
    model = request.args.get("model")
    if model is None:
        return jsonify({"status": "error", "message": "missing required query param 'model'"}), 400
    _dt.outer_evolve(model)
    return jsonify({"status": "ok", "action": "outer_evolve", "model": model})

if __name__ == "__main__":
    app.run(host="0.0.0.0", port=5000)