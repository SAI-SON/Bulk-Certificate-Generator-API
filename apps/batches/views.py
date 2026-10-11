import csv
import os

from django.conf import settings
from django.core.files.base import ContentFile
from django.http import HttpResponse, FileResponse
from django.utils import timezone
from rest_framework import viewsets, status
from rest_framework.decorators import action
from rest_framework.response import Response
from rest_framework.permissions import IsAuthenticated
from rest_framework.parsers import MultiPartParser, FormParser, JSONParser

from apps.accounts.permissions import IsOwner
from apps.certificates.models import Certificate
from apps.certificates.serializers import CertificateSerializer
from .models import CertificateBatch
from .serializers import CertificateBatchSerializer, CertificateBatchDetailSerializer
from services.certificate_id import generate_certificate_id
from services.file_parser import ParticipantFileParser, FileParserError
from services.pdf_generator import PDFGenerator, PDFGenerationError
from drf_spectacular.utils import extend_schema, OpenApiResponse, OpenApiParameter, OpenApiTypes


class CertificateBatchViewSet(viewsets.ModelViewSet):
    """
    API endpoints for managing certificate batches.
    """
    permission_classes = [IsAuthenticated, IsOwner]
    parser_classes = [MultiPartParser, FormParser, JSONParser]
    def initial(self, request, *args, **kwargs):
        # Support token authentication via query parameter for direct browser downloads
        token = request.query_params.get("token")
        if token and "HTTP_AUTHORIZATION" not in request.META:
            request.META["HTTP_AUTHORIZATION"] = f"Token {token}"
        super().initial(request, *args, **kwargs)

    def get_queryset(self):
        return CertificateBatch.objects.filter(owner=self.request.user)

    def get_serializer_class(self):
        if self.action in ["retrieve"]:
            return CertificateBatchDetailSerializer
        return CertificateBatchSerializer

    @extend_schema(
        summary="Validate Batch CSV/XLSX File",
        description="Parses the uploaded participant file, validating headers, email formats, and duplicates.",
        responses={
            200: OpenApiResponse(description="Validation passed (fully or partially). Returns counts of valid and invalid rows."),
            400: OpenApiResponse(description="Validation failed completely (e.g. invalid file format).")
        }
    )
    @action(detail=True, methods=["post"])
    def validate(self, request, pk=None):
        batch = self.get_object()
        
        if batch.status not in ["uploaded", "failed"]:
            return Response(
                {"detail": f"Cannot validate batch in '{batch.status}' state."},
                status=status.HTTP_400_BAD_REQUEST
            )
            
        try:
            parser = ParticipantFileParser(batch.participant_file.path)
            valid_rows, errors, total_rows = parser.parse()
            
            batch.total_records = total_rows
            
            if errors:
                batch.error_summary = {"validation_errors": errors}
                if valid_rows:
                    batch.status = "validated"
                else:
                    batch.status = "failed"
            else:
                batch.error_summary = {}
                batch.status = "validated"
                
            batch.save()
            
            return Response({
                "total_rows": total_rows,
                "valid_rows": len(valid_rows),
                "invalid_rows": len(errors),
                "status": batch.status,
                "errors": errors[:50]
            })
            
        except FileParserError as e:
            batch.status = "failed"
            batch.error_summary = {"critical_error": str(e)}
            batch.save()
            return Response({"detail": str(e)}, status=status.HTTP_400_BAD_REQUEST)
        except Exception:
            batch.status = "failed"
            batch.error_summary = {"critical_error": "An unexpected error occurred during validation."}
            batch.save()
            return Response({"detail": "Failed to process file."}, status=status.HTTP_500_INTERNAL_SERVER_ERROR)

    @extend_schema(
        summary="Start Certificate Generation",
        description="Generates certificates for the validated batch. Processes synchronously for small batches, or queues a Celery task for large batches.",
        responses={
            200: OpenApiResponse(description="Batch generation completed synchronously."),
            202: OpenApiResponse(description="Batch queued for asynchronous generation via Celery."),
            400: OpenApiResponse(description="Batch is not in a valid state to generate.")
        }
    )
    @action(detail=True, methods=["post"])
    def generate(self, request, pk=None):
        """
        Start the certificate generation process.
        For small batches, process synchronously.
        For large batches (Phase 7), delegate to Celery.
        """
        batch = self.get_object()
        
        if batch.status != "validated":
            return Response(
                {"detail": f"Batch must be in 'validated' state to start generation. Current state: '{batch.status}'."},
                status=status.HTTP_400_BAD_REQUEST
            )
            
        parser = ParticipantFileParser(batch.participant_file.path)
        valid_rows, _, _ = parser.parse()
        
        if not valid_rows:
            return Response(
                {"detail": "No valid rows to process."},
                status=status.HTTP_400_BAD_REQUEST
            )
            
        # Clear previous stats
        batch.processed_records = 0
        batch.successful_records = 0
        batch.failed_records = 0
        batch.started_at = timezone.now()
        batch.status = "processing"
        batch.save()
        
        if len(valid_rows) <= settings.SYNC_GENERATION_THRESHOLD:
            # Synchronous processing
            self._process_batch_sync(batch, valid_rows)
            return Response({
                "detail": "Batch generation completed.",
                "status": batch.status
            })
        else:
            # Async processing (Phase 7)
            batch.status = "queued"
            batch.save(update_fields=["status"])
            
            # Trigger Celery task
            from tasks.generation import generate_certificates_task
            generate_certificates_task.delay(str(batch.id))
            
            return Response(
                {"detail": "Batch queued for asynchronous generation."},
                status=status.HTTP_202_ACCEPTED
            )
            
    def _process_batch_sync(self, batch, valid_rows):
        pdf_gen = PDFGenerator()
        field_config = batch.template.field_configuration
        template_path = batch.template.template_file.path
        
        for row in valid_rows:
            try:
                pdf_buffer, cert_id = pdf_gen.generate(template_path, row, field_config)
                
                # Sanitize filename
                safe_name = "".join([c for c in row.get("name", "Unknown") if c.isalpha() or c.isdigit() or c in " -_"]).rstrip()
                filename = f"{cert_id}_{safe_name}.pdf"
                
                cert = Certificate(
                    batch=batch,
                    recipient_name=row.get("name"),
                    recipient_email=row.get("email"),
                    course_name=row.get("course_name", ""),
                    completion_date=row.get("completion_date"),
                    certificate_id=cert_id,
                    status="generated"
                )
                cert.generated_file.save(filename, ContentFile(pdf_buffer.getvalue()), save=True)
                
                batch.successful_records += 1
            except PDFGenerationError as e:
                Certificate.objects.create(
                    batch=batch,
                    recipient_name=row.get("name"),
                    recipient_email=row.get("email"),
                    certificate_id=generate_certificate_id(),
                    status="failed",
                    error_message=str(e)
                )
                batch.failed_records += 1
            except Exception as e:
                Certificate.objects.create(
                    batch=batch,
                    recipient_name=row.get("name"),
                    recipient_email=row.get("email"),
                    certificate_id=generate_certificate_id(),
                    status="failed",
                    error_message=f"System error: {str(e)}"
                )
                batch.failed_records += 1
                
            batch.processed_records += 1
            batch.save(update_fields=["processed_records", "successful_records", "failed_records"])
            
        batch.completed_at = timezone.now()
        batch.status = "completed" if batch.failed_records == 0 else "partially_completed"
        batch.save()

    @extend_schema(
        summary="Get Batch Status",
        description="Returns the real-time processing status and progress percentage of a batch.",
        responses={200: OpenApiResponse(description="Current status payload")}
    )
    @action(detail=True, methods=["get"])
    def status(self, request, pk=None):
        batch = self.get_object()
        
        progress = 0
        if batch.total_records > 0:
            progress = int((batch.processed_records / batch.total_records) * 100)
            
        return Response({
            "batch_id": batch.id,
            "status": batch.status,
            "total": batch.total_records,
            "processed": batch.processed_records,
            "successful": batch.successful_records,
            "failed": batch.failed_records,
            "progress_percentage": progress,
            "started_at": batch.started_at,
            "completed_at": batch.completed_at,
            "errors": batch.error_summary
        })

    @extend_schema(
        summary="List Batch Certificates",
        description="Paginated list of all certificates (generated or failed) belonging to this batch.",
        responses={200: CertificateSerializer(many=True)}
    )
    @action(detail=True, methods=["get"])
    def certificates(self, request, pk=None):
        """
        List certificates belonging to this batch.
        """
        batch = self.get_object()
        queryset = batch.certificates.all()
        
        page = self.paginate_queryset(queryset)
        if page is not None:
            serializer = CertificateSerializer(page, many=True)
            return self.get_paginated_response(serializer.data)
            
        serializer = CertificateSerializer(queryset, many=True)
        return Response(serializer.data)

    @extend_schema(
        summary="Cancel Queued Batch",
        description="Cancels a batch that is waiting in the queue to be processed.",
        responses={
            200: OpenApiResponse(description="Batch cancelled successfully."),
            400: OpenApiResponse(description="Batch is not queued and cannot be cancelled.")
        }
    )
    @action(detail=True, methods=["post"])
    def cancel(self, request, pk=None):
        batch = self.get_object()
        if batch.status == "queued":
            batch.status = "failed"
            batch.error_summary = {"critical_error": "Job was cancelled by the user."}
            batch.save(update_fields=["status", "error_summary"])
            return Response({"detail": "Batch cancelled successfully."})
        return Response({"detail": f"Cannot cancel a batch in '{batch.status}' status."}, status=status.HTTP_400_BAD_REQUEST)

    @extend_schema(
        summary="Retry Failed Certificates",
        description="Queues a task to retry generation only for the certificates that failed in a previous run.",
        responses={
            202: OpenApiResponse(description="Retry job queued successfully."),
            400: OpenApiResponse(description="No failed certificates or batch is not in a completed state.")
        }
    )
    @action(detail=True, methods=["post"])
    def retry_failed(self, request, pk=None):
        batch = self.get_object()
        if batch.status not in ["completed", "partially_completed", "failed"]:
            return Response({"detail": "Batch is still processing or not generated yet."}, status=status.HTTP_400_BAD_REQUEST)

        failed_certs = batch.certificates.filter(status="failed")
        if not failed_certs.exists():
            return Response({"detail": "No failed certificates found to retry."}, status=status.HTTP_400_BAD_REQUEST)

        failed_count = failed_certs.count()

        # Reset batch counters for the retry run
        batch.status = "queued"
        batch.failed_records = 0
        batch.processed_records = batch.successful_records  # Keep existing successes
        batch.save(update_fields=["status", "failed_records", "processed_records"])
        
        # Trigger Celery task — the task deletes old failed certs and re-processes.
        from tasks.generation import generate_certificates_task
        generate_certificates_task.delay(str(batch.id))

        return Response({"detail": f"Queued {failed_count} failed certificates for retry."}, status=status.HTTP_202_ACCEPTED)

    @extend_schema(
        summary="Download Failed Report",
        description="Downloads a CSV report of all failed certificates, including error messages.",
        responses={200: OpenApiResponse(description="CSV File Stream")}
    )
    @action(detail=True, methods=["get"], url_path="failed-report")
    def failed_report(self, request, pk=None):
        batch = self.get_object()
        failed_certs = batch.certificates.filter(status="failed")
        
        response = HttpResponse(
            content_type="text/csv",
            headers={"Content-Disposition": f'attachment; filename="failed_report_{batch.id}.csv"'},
        )
        writer = csv.writer(response)
        writer.writerow(["recipient_name", "recipient_email", "error_message", "created_at"])
        
        for cert in failed_certs:
            writer.writerow([cert.recipient_name, cert.recipient_email, cert.error_message, cert.created_at])
            
        return response

    @extend_schema(
        summary="Download Certificates ZIP",
        description="Generates and streams a ZIP file containing all successfully generated PDFs for this batch.",
        responses={
            200: OpenApiResponse(description="ZIP File Stream"),
            400: OpenApiResponse(description="Batch not completed."),
            404: OpenApiResponse(description="No successful certificates found.")
        }
    )
    @action(detail=True, methods=["get"], url_path="download-zip")
    def download_zip(self, request, pk=None):
        batch = self.get_object()
        
        if batch.status not in ["completed", "partially_completed"]:
            return Response({"detail": "No certificates generated yet."}, status=status.HTTP_400_BAD_REQUEST)
            
        from services.zip_builder import ZipBuilder
        zip_path = ZipBuilder.build_certificates_zip(batch)
        
        if not zip_path:
            return Response({"detail": "No successful certificates found."}, status=status.HTTP_404_NOT_FOUND)
        
        # Open the temp file and schedule cleanup after response is sent
        zip_file = open(zip_path, 'rb')
        response = FileResponse(zip_file, as_attachment=True, filename=f"{batch.name}_certificates.zip")
        # Clean up the temp file after the response is streamed
        response.file_to_stream_with_cleanup = zip_path
        import atexit
        atexit.register(lambda p=zip_path: os.path.exists(p) and os.unlink(p))
        return response

    @extend_schema(
        summary="Download Original Uploaded File",
        description="Downloads the raw CSV/XLSX file originally uploaded by the user.",
        responses={
            200: OpenApiResponse(description="Raw file stream"),
            404: OpenApiResponse(description="File not found on server.")
        }
    )
    @action(detail=True, methods=["get"], url_path="download-original")
    def download_original(self, request, pk=None):
        batch = self.get_object()
        if not batch.participant_file:
            return Response({"detail": "No file uploaded."}, status=status.HTTP_404_NOT_FOUND)
            
        return FileResponse(
            batch.participant_file.open('rb'), 
            as_attachment=True, 
            filename=os.path.basename(batch.participant_file.name)
        )


