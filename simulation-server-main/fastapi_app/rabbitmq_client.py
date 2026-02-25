import pika
import json
import os

RABBITMQ_HOST = os.environ.get("RABBITMQ_HOST", "rabbitmq")


class SimulationQueue:
    def __init__(self):
        self.connection = pika.BlockingConnection(
            pika.ConnectionParameters(host=RABBITMQ_HOST)
        )
        self.channel = self.connection.channel()
        self.channel.queue_declare(queue="simulation_requests", durable=True)

    def publish(self, task_id: str, payload: dict):
        message = {"task_id": task_id, "payload": payload}
        self.channel.basic_publish(
            exchange="",
            routing_key="simulation_requests",
            body=json.dumps(message),
            properties=pika.BasicProperties(delivery_mode=2),
        )

    def close(self):
        self.connection.close()
