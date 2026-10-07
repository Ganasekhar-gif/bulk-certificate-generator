import os
import shutil
import tempfile
from unittest.mock import patch

from app.certificate_generator import CertificateGenerator
from app.models import Certificate, CertificateStatus, Job, JobStatus
from app.tasks import run_certificate_job


def test_run_certificate_job_success(db_session):
    job = Job(status=JobStatus.PENDING, total_recipients=2)
    db_session.add(job)
    db_session.commit()

    for name in ("Alice", "Bob"):
        db_session.add(
            Certificate(
                job_id=job.id,
                recipient_name=name,
                recipient_email=f"{name.lower()}@example.com",
                course_name="Test Course",
                completion_date="2024-06-01",
            )
        )
    db_session.commit()

    temp_dir = tempfile.mkdtemp()
    try:
        generator = CertificateGenerator(output_dir=temp_dir)
        result = run_certificate_job(db_session, job.id, generator=generator)

        assert result["successful_count"] == 2
        assert result["failed_count"] == 0
        assert result["status"] == "completed"

        db_session.refresh(job)
        assert job.status == JobStatus.COMPLETED

        certs = (
            db_session.query(Certificate).filter(Certificate.job_id == job.id).all()
        )
        assert all(c.status == CertificateStatus.SUCCESS for c in certs)
        assert all(c.certificate_path and os.path.isfile(c.certificate_path) for c in certs)
    finally:
        shutil.rmtree(temp_dir, ignore_errors=True)


def test_run_certificate_job_one_failure_does_not_block_others(db_session):
    job = Job(status=JobStatus.PENDING, total_recipients=2)
    db_session.add(job)
    db_session.commit()

    db_session.add(
        Certificate(
            job_id=job.id,
            recipient_name="Good User",
            recipient_email="good@example.com",
            course_name="Test Course",
            completion_date="2024-06-01",
        )
    )
    db_session.add(
        Certificate(
            job_id=job.id,
            recipient_name="Bad User",
            recipient_email="bad@example.com",
            course_name="Test Course",
            completion_date="2024-06-01",
        )
    )
    db_session.commit()

    temp_dir = tempfile.mkdtemp()
    try:
        generator = CertificateGenerator(output_dir=temp_dir)
        original = generator.generate_certificate

        def generate_with_failure(**kwargs):
            if kwargs["recipient_name"] == "Bad User":
                raise RuntimeError("Simulated PDF error")
            return original(**kwargs)

        with patch.object(generator, "generate_certificate", side_effect=generate_with_failure):
            result = run_certificate_job(db_session, job.id, generator=generator)

        assert result["successful_count"] == 1
        assert result["failed_count"] == 1

        db_session.refresh(job)
        assert job.status == JobStatus.COMPLETED
        assert "Partial success" in (job.error_message or "")

        certs = {
            c.recipient_name: c
            for c in db_session.query(Certificate).filter(Certificate.job_id == job.id).all()
        }
        assert certs["Good User"].status == CertificateStatus.SUCCESS
        assert certs["Bad User"].status == CertificateStatus.FAILED
    finally:
        shutil.rmtree(temp_dir, ignore_errors=True)
