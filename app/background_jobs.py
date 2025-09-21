import json
import logging
from typing import Dict, Any
from datetime import datetime
from sqlalchemy.orm import Session
from app.rabbitmq import rabbitmq_client
from app.services import BackgroundJobService
from app.database import SessionLocal

logger = logging.getLogger(__name__)


class BackgroundJobProcessor:
    """Process background jobs from RabbitMQ"""
    
    def __init__(self):
        self.job_handlers = {
            'send_email': self._handle_email_job,
            'data_processing': self._handle_data_processing_job,
            'notification': self._handle_notification_job,
            'cleanup': self._handle_cleanup_job,
        }
    
    def process_job(self, ch, method, properties, body):
        """Process a background job"""
        try:
            # Parse message
            message = json.loads(body)
            job_id = message.get('job_id')
            job_type = message.get('job_type')
            payload = message.get('payload', {})
            
            logger.info(f"Processing job {job_id} of type {job_type}")
            
            # Update job status to processing
            db = SessionLocal()
            try:
                BackgroundJobService.update_job_status(db, job_id, "processing")
                
                # Execute job handler
                if job_type in self.job_handlers:
                    result = self.job_handlers[job_type](payload)
                    BackgroundJobService.update_job_status(
                        db, job_id, "completed", result=str(result)
                    )
                    logger.info(f"Job {job_id} completed successfully")
                else:
                    error_msg = f"Unknown job type: {job_type}"
                    BackgroundJobService.update_job_status(
                        db, job_id, "failed", error_message=error_msg
                    )
                    logger.error(f"Job {job_id} failed: {error_msg}")
                
            finally:
                db.close()
            
            # Acknowledge message
            ch.basic_ack(delivery_tag=method.delivery_tag)
            
        except Exception as e:
            logger.error(f"Error processing job: {e}")
            # Update job status to failed
            try:
                db = SessionLocal()
                BackgroundJobService.update_job_status(
                    db, job_id, "failed", error_message=str(e)
                )
                db.close()
            except:
                pass
            
            # Reject message
            ch.basic_nack(delivery_tag=method.delivery_tag, requeue=False)
    
    def _handle_email_job(self, payload: Dict[str, Any]) -> str:
        """Handle email sending job"""
        # Simulate email sending
        import time
        time.sleep(2)  # Simulate processing time
        
        to_email = payload.get('to_email')
        subject = payload.get('subject')
        body = payload.get('body')
        
        logger.info(f"Sending email to {to_email} with subject: {subject}")
        
        # Here you would integrate with actual email service
        # For demo purposes, we'll just log it
        return f"Email sent to {to_email}"
    
    def _handle_data_processing_job(self, payload: Dict[str, Any]) -> str:
        """Handle data processing job"""
        import time
        time.sleep(3)  # Simulate processing time
        
        data_size = payload.get('data_size', 0)
        logger.info(f"Processing {data_size} records")
        
        # Simulate data processing
        processed_count = data_size * 0.8  # 80% success rate
        
        return f"Processed {processed_count} out of {data_size} records"
    
    def _handle_notification_job(self, payload: Dict[str, Any]) -> str:
        """Handle notification job"""
        import time
        time.sleep(1)  # Simulate processing time
        
        message = payload.get('message', '')
        user_id = payload.get('user_id')
        
        logger.info(f"Sending notification to user {user_id}: {message}")
        
        return f"Notification sent to user {user_id}"
    
    def _handle_cleanup_job(self, payload: Dict[str, Any]) -> str:
        """Handle cleanup job"""
        import time
        time.sleep(2)  # Simulate processing time
        
        cleanup_type = payload.get('type', 'general')
        logger.info(f"Performing {cleanup_type} cleanup")
        
        return f"Cleanup completed: {cleanup_type}"


def publish_background_job(job_type: str, payload: Dict[str, Any] = None) -> str:
    """Publish a background job to RabbitMQ"""
    import uuid
    
    job_id = str(uuid.uuid4())
    message = {
        'job_id': job_id,
        'job_type': job_type,
        'payload': payload or {},
        'created_at': datetime.utcnow().isoformat()
    }
    
    routing_key = f"jobs.{job_type}"
    
    success = rabbitmq_client.publish_message(routing_key, message)
    if success:
        logger.info(f"Published background job {job_id} of type {job_type}")
        return job_id
    else:
        raise Exception("Failed to publish background job")


def start_job_processor():
    """Start the background job processor"""
    processor = BackgroundJobProcessor()
    
    try:
        rabbitmq_client.consume_messages('background_jobs', processor.process_job)
    except KeyboardInterrupt:
        logger.info("Stopping job processor...")
        rabbitmq_client.stop_consuming()
        rabbitmq_client.disconnect()
    except Exception as e:
        logger.error(f"Error in job processor: {e}")
        raise
