import sys
import os
import configparser

this_directory = os.path.dirname(os.path.abspath(__file__))

for subdir in ['PythonBaseWrapper/src/logic', 'PythonBaseWrapper/src/communication',
               '../PythonBaseWrapper/src/logic', '../PythonBaseWrapper/src/communication',
               '/app/PythonBaseWrapper/src/logic', '/app/PythonBaseWrapper/src/communication']:
    path = os.path.join(this_directory, subdir) if not subdir.startswith('/') else subdir
    if os.path.exists(path):
        sys.path.append(path)

try:
    from TimeSync import TimeSync
    from KafkaConsumer import KafkaConsumer
    from KafkaProducer import KafkaProducer
except ImportError:
    print("Warning: PythonBaseWrapper modules not found.")
    TimeSync = KafkaConsumer = KafkaProducer = None

from pandapowerApi import pandapowerAPI


class PandapowerWrapper:
    def __init__(self, scenarioID, instanceID, config_path='/data/config.properties'):
        self.scenarioID = scenarioID
        self.instanceID = instanceID
        
        config = configparser.ConfigParser()
        config.read(config_path)
        
        def get_config(key, fallback):
            return os.getenv(key, config.get('general', key, fallback=fallback))
        
        self.broker = get_config('kafkaBroker', 'localhost:9092')
        self.registry = get_config('schemaRegistry', 'http://localhost:8081')
        self.resource_dir = get_config('resourceDir', '/data/resources')
        self.results_dir = get_config('resultsDir', '/data/results')
        
        self.kid = f"{scenarioID}.{instanceID}"
        self.topic_scenario = [f"provision.simulation.{scenarioID}.scenario"]
        self.topic_time = f"orchestration.simulation.{scenarioID}.sync"
        self.topic_status = f"orchestration.simulation.{scenarioID}.status"
        
        self.status_producer = KafkaProducer(self.broker, self.registry, self.kid, useAvro=False) if KafkaProducer else None
        self.sim_config = None
        self.scenario_data = None
        self.network_file = None
        self.api = None
        self.timeSync = None

    def log(self, msg):
        print(f"[{self.instanceID}] {msg}", flush=True)
        if self.status_producer:
            try:
                self.status_producer.produce(self.topic_status, f"{self.instanceID}: {msg}")
            except:
                pass

    def wait_for_scenario(self):
        self.log("Waiting for scenario...")
        consumer = KafkaConsumer(self.broker, self.registry, self.topic_scenario, self.kid + ".sce")
        
        while True:
            msg = consumer.poll(1.0)
            if msg is None or msg.error():
                continue
            scenario = msg.value()
            for block in scenario.get('buildingBlocks', []):
                if block['instanceID'] == self.instanceID:
                    self.sim_config = block
                    self.scenario_data = scenario
                    self.log(f"Found config for {self.instanceID}")
                    break
            if self.sim_config:
                break
        consumer.stop()
        
        for res_id, res_type in self.sim_config.get('resources', {}).items():
            if res_type == 'Network':
                self.network_file = res_id
                break
        
        if not self.network_file:
            self.log("ERROR: No Network resource found")
            sys.exit(1)

    def run(self):
        self.wait_for_scenario()
        
        net_path = os.path.join(self.resource_dir, self.network_file)
        self.log(f"Loading network: {net_path}")
        
        step_size = self.sim_config.get('stepLength', 1000)
        sim_end = self.scenario_data.get('simulationEnd', 1000)
        n_steps = max(1, sim_end // step_size)
        
        self.api = pandapowerAPI(net_path, step_size, n_steps, self.results_dir)
        self.api.init()
        
        synced = self.scenario_data.get('execution', {}).get('syncedParticipants', 1)
        self.timeSync = TimeSync(self.broker, self.registry, self.topic_time, self.kid + ".ts", synced, logging=False)
        self.timeSync.joinTiming()
        self.log("TimeSync joined. Running simulation...")

        try:
            for step in range(n_steps):
                self.timeSync.timeAdvance(step_size)
                self.log(f"Step {step}")
                self.api.prepareStep(step)
                self.api.step(step)
        except Exception as e:
            self.log(f"Error: {e}")
        finally:
            self.log("Exporting results...")
            self.api.export_results()
            self.timeSync.leaveTiming()
            self.log("Done.")


def main():
    if len(sys.argv) > 2:
        scenarioID, instanceID = sys.argv[1], sys.argv[2]
    else:
        print("Usage: python pandapowerWrapper.py <scenarioID> <instanceID>")
        sys.exit(1)

    wrapper = PandapowerWrapper(scenarioID, instanceID)
    wrapper.run()


if __name__ == '__main__':
    main()
