"""
Minimal DaceDS Worker - Demonstrates the protocol flow.
"""
import pika, redis, json, os, time

# Config
RABBITMQ_HOST = os.environ.get("RABBITMQ_HOST", "rabbitmq")
REDIS_HOST = os.environ.get("REDIS_HOST", "redis")
RESULTS_DIR = os.environ.get("RESULTS_DIR", "/data/results")

def main():
    # 1. Connect to RabbitMQ (with retry)
    while True:
        try:
            rmq = pika.BlockingConnection(pika.ConnectionParameters(host=RABBITMQ_HOST))
            break
        except pika.exceptions.AMQPConnectionError:
            print("Waiting for RabbitMQ...")
            time.sleep(3)
    
    channel = rmq.channel()
    channel.queue_declare(queue="simulation_requests", durable=True)
    channel.basic_qos(prefetch_count=1)
    
    # 2. Connect to Redis
    r = redis.Redis(host=REDIS_HOST, port=6379, db=0)

    def on_request(ch, method, props, body):
        # 3. Parse Request
        msg = json.loads(body)
        task_id = msg["task_id"]
        print(f"Received task: {task_id}")
        
        # 4. Report 'RUNNING'
        r.hset(f"task:{task_id}", "status", "RUNNING")
        
        # 5. Simulate Work (Read inputs -> Write outputs)
        # Inputs at: /data/resources/{task_id}/
        # Outputs at: /data/results/{task_id}/
        result_dir = os.path.join(RESULTS_DIR, task_id)
        os.makedirs(result_dir, exist_ok=True)
        
        output_file = "result.json"
        with open(os.path.join(result_dir, output_file), "w") as f:
            json.dump({"status": "success", "processed_inputs": msg["payload"].get("files")}, f)
            
        # 6. Report 'DONE'
        r.hset(f"task:{task_id}", mapping={"status": "DONE", "files": json.dumps([output_file])})
        
        # 7. Acknowledge
        ch.basic_ack(delivery_tag=method.delivery_tag)
        print(f"Finished task: {task_id}")

    channel.basic_consume(queue="simulation_requests", on_message_callback=on_request)
    print("Worker started. Waiting for tasks...")
    channel.start_consuming()

if __name__ == "__main__":
    main()
