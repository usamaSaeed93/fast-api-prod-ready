import logging
import sys
import time
from datetime import datetime
from app.core.logging import configure_logging, get_logger
from app.core.message_queue import JobConsumer, message_queue_manager
from app.core.database import get_db_context
from app.services.job_service import BackgroundJobService
from app.schemas.job import JobStatusUpdate, JobStatus
from app.core.config import settings

logger = get_logger(__name__)


class EmailJobHandler:
    @staticmethod
    def handle_email_job(payload: dict) -> str:
        logger.info("Processing email job", payload=payload)
        
        to_email = payload.get("to_email")
        subject = payload.get("subject")
        body = payload.get("body")
        is_html = payload.get("is_html", False)
        
        time.sleep(2)
        
        logger.info(f"Email sent to {to_email}", subject=subject)
        return f"Email sent to {to_email}"


class NotificationJobHandler:
    @staticmethod
    def handle_notification_job(payload: dict) -> str:
        logger.info("Processing notification job", payload=payload)
        
        message = payload.get("message")
        notification_type = payload.get("notification_type", "info")
        user_id = payload.get("user_id")
        
        time.sleep(1)
        
        logger.info(f"Notification sent to user {user_id}", type=notification_type)
        return f"Notification sent to user {user_id}"


class DataProcessingJobHandler:
    @staticmethod
    def handle_data_processing_job(payload: dict) -> str:
        logger.info("Processing data processing job", payload=payload)
        
        data_source = payload.get("data_source")
        processing_type = payload.get("processing_type")
        parameters = payload.get("parameters", {})
        
        time.sleep(3)
        
        processed_count = parameters.get("count", 100) * 0.8
        
        logger.info(f"Data processing completed", source=data_source, type=processing_type)
        return f"Processed {processed_count} records from {data_source}"


class CleanupJobHandler:
    @staticmethod
    def handle_cleanup_job(payload: dict) -> str:
        logger.info("Processing cleanup job", payload=payload)
        
        cleanup_type = payload.get("cleanup_type", "general")
        older_than_days = payload.get("older_than_days", 30)
        dry_run = payload.get("dry_run", False)
        
        time.sleep(2)
        
        if dry_run:
            logger.info(f"Cleanup dry run completed", type=cleanup_type, days=older_than_days)
            return f"Cleanup dry run completed: {cleanup_type}"
        else:
            logger.info(f"Cleanup completed", type=cleanup_type, days=older_than_days)
            return f"Cleanup completed: {cleanup_type}"


class BackgroundJobProcessor:
    def __init__(self):
        self.job_handlers = {
            "send_email": EmailJobHandler.handle_email_job,
            "notification": NotificationJobHandler.handle_notification_job,
            "data_processing": DataProcessingJobHandler.handle_data_processing_job,
            "cleanup": CleanupJobHandler.handle_cleanup_job,
        }
    
    def process_job(self, ch, method, properties, body):
        import json
        
        try:
            message = json.loads(body)
            job_id = message.get("job_id")
            job_type = message.get("job_type")
            payload = message.get("payload", {})
            
            logger.info("Processing job", job_id=job_id, job_type=job_type)
            
            with get_db_context() as db:
                BackgroundJobService.update_job_status(
                    db, job_id, JobStatusUpdate(status=JobStatus.PROCESSING)
                )
                
                if job_type in self.job_handlers:
                    result = self.job_handlers[job_type](payload)
                    BackgroundJobService.update_job_status(
                        db, job_id, JobStatusUpdate(status=JobStatus.COMPLETED, result=result)
                    )
                    logger.info("Job completed successfully", job_id=job_id)
                else:
                    error_msg = f"Unknown job type: {job_type}"
                    BackgroundJobService.update_job_status(
                        db, job_id, JobStatusUpdate(status=JobStatus.FAILED, error_message=error_msg)
                    )
                    logger.error("Job failed", job_id=job_id, error=error_msg)
                
            ch.basic_ack(delivery_tag=method.delivery_tag)
            
        except Exception as e:
            logger.error("Error processing job", error=str(e), exc_info=True)
            
            try:
                with get_db_context() as db:
                    BackgroundJobService.update_job_status(
                        db, job_id, JobStatusUpdate(status=JobStatus.FAILED, error_message=str(e))
                    )
            except Exception as db_error:
                logger.error("Failed to update job status", error=str(db_error))
            
            ch.basic_nack(delivery_tag=method.delivery_tag, requeue=False)


def start_job_processor():
    configure_logging()
    logger.info("Starting background job processor")
    
    processor = BackgroundJobProcessor()
    consumer = JobConsumer(processor.job_handlers)
    
    try:
        consumer.start_consuming("background_jobs")
    except KeyboardInterrupt:
        logger.info("Background job processor stopped by user")
        consumer.stop_consuming()
        message_queue_manager.disconnect()
    except Exception as e:
        logger.error("Background job processor failed", error=str(e))
        sys.exit(1)


if __name__ == "__main__":
    start_job_processor()