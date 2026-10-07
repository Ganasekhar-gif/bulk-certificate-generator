from datetime import datetime, timezone
import traceback
from typing import Optional

from sqlalchemy.orm import Session

from app.celery_app import celery_app
from app.certificate_generator import CertificateGenerator
from app.config import get_settings
from app.database import SessionLocal
from app.models import Certificate, CertificateStatus, Job, JobStatus


def run_certificate_job(
    db: Session,
    job_id: int,
    generator: Optional[CertificateGenerator] = None,
) -> dict:
    """
    Generate PDFs for every certificate row in a job.
    Each recipient is processed independently so one failure does not block the rest.
    """
    job = db.query(Job).filter(Job.id == job_id).first()
    if not job:
        raise ValueError(f"Job {job_id} not found")

    job.status = JobStatus.PROCESSING
    db.commit()

    if generator is None:
        settings = get_settings()
        generator = CertificateGenerator(output_dir=settings.certificate_output_dir)

    certificates = db.query(Certificate).filter(Certificate.job_id == job_id).all()

    successful_count = 0
    failed_count = 0

    for cert in certificates:
        try:
            file_path, _filename = generator.generate_certificate(
                recipient_name=cert.recipient_name,
                recipient_email=cert.recipient_email,
                course_name=cert.course_name,
                completion_date=cert.completion_date,
            )
            cert.status = CertificateStatus.SUCCESS
            cert.certificate_path = file_path
            cert.error_message = None
            successful_count += 1
        except Exception as e:
            cert.status = CertificateStatus.FAILED
            cert.error_message = (
                f"Failed to generate certificate for {cert.recipient_name}: {e}"
            )
            failed_count += 1
        db.commit()

    job.successful_count = successful_count
    job.failed_count = failed_count
    job.completed_at = datetime.now(timezone.utc)

    if failed_count == 0:
        job.status = JobStatus.COMPLETED
        job.error_message = None
    elif successful_count == 0:
        job.status = JobStatus.FAILED
        job.error_message = "All certificate generations failed"
    else:
        job.status = JobStatus.COMPLETED
        job.error_message = (
            f"Partial success: {successful_count} succeeded, {failed_count} failed"
        )

    db.commit()

    return {
        "job_id": job_id,
        "status": job.status.value,
        "successful_count": successful_count,
        "failed_count": failed_count,
    }


@celery_app.task(bind=True)
def process_certificate_generation(self, job_id: int):
    """Celery entry point: opens a DB session and runs the shared job processor."""
    db = SessionLocal()
    job = None
    try:
        return run_certificate_job(db, job_id)
    except Exception as e:
        job = db.query(Job).filter(Job.id == job_id).first()
        if job:
            job.status = JobStatus.FAILED
            job.error_message = f"Job processing failed: {e}\n{traceback.format_exc()}"
            job.completed_at = datetime.now(timezone.utc)
            db.commit()
        raise
    finally:
        db.close()
