import json
import os
import pika

QUEUE_NAME = os.getenv("PAYMENTS_QUEUE", "payments")

def publish_payment_created(message: dict) -> None:
    """
    Publish a payment_created event to RabbitMQ.
    Uses RABBIT_URL from env (set in deploy compose).
    """
    rabbit_url = os.getenv("RABBIT_URL")
    if not rabbit_url:
        # If Rabbit isn't configured, do nothing (keeps dev/test stable)
        return

    params = pika.URLParameters(rabbit_url)
    connection = pika.BlockingConnection(params)
    try:
        channel = connection.channel()
        channel.queue_declare(queue=QUEUE_NAME, durable=True)

        body = json.dumps(message).encode("utf-8")
        channel.basic_publish(
            exchange="",
            routing_key=QUEUE_NAME,
            body=body,
            properties=pika.BasicProperties(delivery_mode=2), 
        )
    finally:
        connection.close()
