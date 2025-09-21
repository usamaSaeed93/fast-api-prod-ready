import pika
import json
import logging
from typing import Dict, Any, Callable
from app.config import settings

logger = logging.getLogger(__name__)


class RabbitMQClient:
    """RabbitMQ client for message publishing and consuming"""
    
    def __init__(self):
        self.connection = None
        self.channel = None
        self.exchange = settings.rabbitmq_exchange
        
    def connect(self):
        """Establish connection to RabbitMQ"""
        try:
            self.connection = pika.BlockingConnection(
                pika.URLParameters(settings.rabbitmq_url)
            )
            self.channel = self.connection.channel()
            
            # Declare exchange
            self.channel.exchange_declare(
                exchange=self.exchange,
                exchange_type='topic',
                durable=True
            )
            
            logger.info("Connected to RabbitMQ successfully")
        except Exception as e:
            logger.error(f"Failed to connect to RabbitMQ: {e}")
            raise
    
    def disconnect(self):
        """Close RabbitMQ connection"""
        if self.connection and not self.connection.is_closed:
            self.connection.close()
            logger.info("Disconnected from RabbitMQ")
    
    def publish_message(self, routing_key: str, message: Dict[str, Any]) -> bool:
        """Publish a message to RabbitMQ"""
        try:
            if not self.channel or self.channel.is_closed:
                self.connect()
            
            message_body = json.dumps(message)
            
            self.channel.basic_publish(
                exchange=self.exchange,
                routing_key=routing_key,
                body=message_body,
                properties=pika.BasicProperties(
                    delivery_mode=2,  # Make message persistent
                    content_type='application/json'
                )
            )
            
            logger.info(f"Published message to {routing_key}: {message}")
            return True
            
        except Exception as e:
            logger.error(f"Failed to publish message: {e}")
            return False
    
    def consume_messages(self, queue_name: str, callback: Callable):
        """Consume messages from a queue"""
        try:
            if not self.channel or self.channel.is_closed:
                self.connect()
            
            # Declare queue
            self.channel.queue_declare(queue=queue_name, durable=True)
            
            # Bind queue to exchange
            self.channel.queue_bind(
                exchange=self.exchange,
                queue=queue_name,
                routing_key=f"{queue_name}.*"
            )
            
            # Set up consumer
            self.channel.basic_qos(prefetch_count=1)
            self.channel.basic_consume(
                queue=queue_name,
                on_message_callback=callback
            )
            
            logger.info(f"Started consuming messages from {queue_name}")
            self.channel.start_consuming()
            
        except Exception as e:
            logger.error(f"Failed to consume messages: {e}")
            raise
    
    def stop_consuming(self):
        """Stop consuming messages"""
        if self.channel and self.channel.is_consuming:
            self.channel.stop_consuming()


# Global RabbitMQ client instance
rabbitmq_client = RabbitMQClient()
