# Wraps the MAPE-K, reads and stores the model, the M, A, P, E components, the knowledge (?)

class DigitalTwin:

    def __init__():
        self.monitor = Monitor()
        self.analyze = Analyze()
        self.plan = Plan()
        self.execute = Execute()

        self.simulation = TBSimulation() # <- this is domain-dependent

        # Setup pika connection

    def run():
        self.monitor.run()

    def inner_evolve():
        ### Changes inside the simulation component

    def outer_evolve():
        self.monitor.update_model(model)
        self.analyze.update_model(model)
        self.plan.update_model(model)