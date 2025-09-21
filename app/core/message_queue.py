import pika
import json
import logging
import time
from typing import Dict, Any, Callable, Optional
from datetime import datetime
from app.core.config import settings
from app.core.monitoring import MetricsCollector

logger = logging.getLogger(__name__)


class MessageQueueManager:
    def __init__(self):
        self.connection = None
        self.channel = None
        self.exchange = settings.message_queue.exchange
        self.queue_prefix = settings.message_queue.queue_prefix
        self.max_retries = settings.message_queue.max_retries
        self.retry_delay = settings.message_queue.retry_delay
        self.prefetch_count = settings.message_queue.prefetch_count
    
    def connect(self) -> bool:
        try:
            self.connection = pika.BlockingConnection(
                pika.URLParameters(settings.message_queue.url)
            )
            self.channel = self.connection.channel()
            
            self.channel.exchange_declare(
                exchange=self.exchange,
                exchange_type='topic',
                durable=True
            )
            
            self.channel.basic_qos(prefetch_count=self.prefetch_count)
            
            logger.info("Connected to RabbitMQ successfully")
            return True
        except Exception as e:
            logger.error(f"Failed to connect to RabbitMQ: {e}")
            return False
    
    def disconnect(self):
        try:
            if self.channel and not self.channel.is_closed:
                self.channel.close()
            if self.connection and not self.connection.is_closed:
                self.connection.close()
            logger.info("Disconnected from RabbitMQ")
        except Exception as e:
            logger.error(f"Error disconnecting from RabbitMQ: {e}")
    
    def publish_message(
        self, 
        routing_key: str, 
        message: Dict[str, Any], 
        priority: int = 0
    ) -> bool:
        try:
            if not self.channel or self.channel.is_closed:
                if not self.connect():
                    return False
            
            message_body = json.dumps(message)
            
            self.channel.basic_publish(
                exchange=self.exchange,
                routing_key=routing_key,
                body=message_body,
                properties=pika.BasicProperties(
                    delivery_mode=2,
                    content_type='application/json',
                    priority=priority,
                    timestamp=int(time.time())
                )
            )
            
            MetricsCollector.record_background_job(
                job_type=routing_key.split('.')[-1],
                status="published"
            )
            
            logger.info(f"Published message to {routing_key}")
            return True
            
        except Exception as e:
            logger.error(f"Failed to publish message: {e}")
            return False
    
    def consume_messages(self, queue_name: str, callback: Callable):
        try:
            if not self.channel or self.channel.is_closed:
                if not self.connect():
                    return
            
            full_queue_name = f"{self.queue_prefix}_{queue_name}"
            
            self.channel.queue_declare(queue=full_queue_name, durable=True)
            
            self.channel.queue_bind(
                exchange=self.exchange,
                queue=full_queue_name,
                routing_key=f"{queue_name}.*"
            )
            
            self.channel.basic_consume(
                queue=full_queue_name,
                on_message_callback=callback
            )
            
            logger.info(f"Started consuming messages from {full_queue_name}")
            self.channel.start_consuming()
            
        except Exception as e:
            logger.error(f"Failed to consume messages: {e}")
            raise
    
    def stop_consuming(self):
        try:
            if self.channel and self.channel.is_consuming:
                self.channel.stop_consuming()
                logger.info("Stopped consuming messages")
        except Exception as e:
            logger.error(f"Error stopping message consumption: {e}")
    
    def health_check(self) -> bool:
        try:
            if not self.connection or self.connection.is_closed:
                return False
            
            self.connection.process_data_events(time_limit=0.1)
            return True
        except Exception as e:
            logger.error(f"RabbitMQ health check failed: {e}")
            return False
    
    def get_queue_info(self, queue_name: str) -> Optional[Dict[str, Any]]:
        try:
            if not self.channel or self.channel.is_closed:
                return None
            
            full_queue_name = f"{self.queue_prefix}_{queue_name}"
            method = self.channel.queue_declare(queue=full_queue_name, passive=True)
            
            return {
                "queue": full_queue_name,
                "message_count": method.method.message_count,
                "consumer_count": method.method.consumer_count
            }
        except Exception as e:
            logger.error(f"Failed to get queue info: {e}")
            return None


message_queue_manager = MessageQueueManager()


class JobPublisher:
    @staticmethod
    def publish_job(
        job_type: str, 
        payload: Dict[str, Any], 
        priority: int = 0
    ) -> bool:
        message = {
            "job_type": job_type,
            "payload": payload,
            "created_at": datetime.utcnow().isoformat(),
            "priority": priority
        }
        
        routing_key = f"jobs.{job_type}"
        return message_queue_manager.publish_message(routing_key, message, priority)


class JobConsumer:
    def __init__(self, job_handlers: Dict[str, Callable]):
        self.job_handlers = job_handlers
    
    def process_message(self, ch, method, properties, body):
        try:
            message = json.loads(body)
            job_type = message.get("job_type")
            payload = message.get("payload", {})
            
            logger.info(f"Processing job: {job_type}")
            
            if job_type in self.job_handlers:
                result = self.job_handlers[job_type](payload)
                MetricsCollector.record_background_job(job_type, "completed")
                logger.info(f"Job completed: {job_type}")
            else:
                logger.error(f"Unknown job type: {job_type}")
                MetricsCollector.record_background_job(job_type, "failed")
            
            ch.basic_ack(delivery_tag=method.delivery_tag)
            
        except Exception as e:
            logger.error(f"Error processing job: {e}")
            MetricsCollector.record_background_job(
                message.get("job_type", "unknown"), 
                "failed"
            )
            
            ch.basic_nack(delivery_tag=method.delivery_tag, requeue=False)
    
    def start_consuming(self, queue_name: str = "background_jobs"):
        message_queue_manager.consume_messages(queue_name, self.process_message)
    
    def stop_consuming(self):
        message_queue_manager.stop_consuming()
