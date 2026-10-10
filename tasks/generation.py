import logging
from datetime import datetime
from celery import shared_task
from django.core.files.base import ContentFile
from django.db import transaction, models

from apps.batches.models import CertificateBatch
from apps.certificates.models import Certificate
from services.file_parser import ParticipantFileParser
from services.pdf_generator import PDFGenerator, PDFGenerationError

logger = logging.getLogger(__name__)


@shared_task(bind=True, max_retries=3)
def generate_certificates_task(self, batch_id):
    """
    Asynchronous task to process a large certificate batch.
    """
    try:
        batch = CertificateBatch.objects.get(id=batch_id)
    except CertificateBatch.DoesNotExist:
        logger.error(f"Batch {batch_id} not found.")
        return "Batch not found"

    if batch.status != "queued":
        logger.warning(f"Batch {batch_id} is in status {batch.status}, skipping execution.")
        return "Not queued"

    # Set status to processing
    batch.status = "processing"
    batch.started_at = datetime.now()
    batch.save(update_fields=["status", "started_at"])

    try:
        parser = ParticipantFileParser(batch.participant_file.path)
        valid_rows, _, _ = parser.parse()

        pdf_gen = PDFGenerator()
        field_config = batch.template.field_configuration
        template_path = batch.template.template_file.path

        for row in valid_rows:
            # Check for existing generated certificate (idempotency)
            # using name and email as a simple unique identifier within a batch
            email = row.get("email", "")
            name = row.get("name", "")
            
            existing = Certificate.objects.filter(
                batch=batch, 
                recipient_name=name, 
                recipient_email=email,
                status="generated"
            ).exists()
            
            if existing:
                continue

            try:
                pdf_buffer, cert_id = pdf_gen.generate(template_path, row, field_config)
                
                safe_name = "".join([c for c in name if c.isalpha() or c.isdigit() or c in " -_"]).rstrip()
                filename = f"{cert_id}_{safe_name}.pdf"
                
                # We wrap the creation in a transaction so failure to save file rolls back DB
                with transaction.atomic():
                    cert = Certificate(
                        batch=batch,
                        recipient_name=name,
                        recipient_email=email,
                        course_name=row.get("course_name", ""),
                        completion_date=row.get("completion_date"),
                        certificate_id=cert_id,
                        status="generated"
                    )
                    cert.generated_file.save(filename, ContentFile(pdf_buffer.getvalue()), save=True)
                    
                # Increment success outside transaction so it's committed immediately
                CertificateBatch.objects.filter(id=batch_id).update(
                    successful_records=models.F("successful_records") + 1,
                    processed_records=models.F("processed_records") + 1
                )
                
            except PDFGenerationError as e:
                Certificate.objects.create(
                    batch=batch,
                    recipient_name=name,
                    recipient_email=email,
                    status="failed",
                    error_message=str(e)
                )
                CertificateBatch.objects.filter(id=batch_id).update(
                    failed_records=models.F("failed_records") + 1,
                    processed_records=models.F("processed_records") + 1
                )
            except Exception as e:
                logger.exception("Error generating certificate for row")
                Certificate.objects.create(
                    batch=batch,
                    recipient_name=name,
                    recipient_email=email,
                    status="failed",
                    error_message=f"System error: {str(e)}"
                )
                CertificateBatch.objects.filter(id=batch_id).update(
                    failed_records=models.F("failed_records") + 1,
                    processed_records=models.F("processed_records") + 1
                )

        # Refresh from db to get accurate counts
        batch.refresh_from_db()
        batch.completed_at = datetime.now()
        batch.status = "completed" if batch.failed_records == 0 else "partially_completed"
        batch.save(update_fields=["completed_at", "status"])

        return f"Completed batch {batch_id} - Success: {batch.successful_records}, Failed: {batch.failed_records}"

    except Exception as exc:
        logger.exception(f"Critical failure processing batch {batch_id}")
        batch.status = "failed"
        batch.error_summary = {"critical_error": "Task failed completely during execution."}
        batch.save(update_fields=["status", "error_summary"])
        
        # Retry for transient errors
        raise self.retry(exc=exc, countdown=60)
