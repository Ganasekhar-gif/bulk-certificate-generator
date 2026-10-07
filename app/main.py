import os

from fastapi import Depends, FastAPI, HTTPException, status
from fastapi.responses import FileResponse, RedirectResponse
from fastapi.staticfiles import StaticFiles
from sqlalchemy.orm import Session

from app.database import Base, engine, get_db
from app.models import Job, Certificate, JobStatus
from app.schemas import JobCreate, JobResponse, JobStatusResponse
from app.tasks import process_certificate_generation

# Create database tables
Base.metadata.create_all(bind=engine)

STATIC_DIR = os.path.join(os.path.dirname(__file__), "static")

app = FastAPI(
    title="Bulk Certificate Generator API",
    description="API for generating certificates in bulk for multiple recipients",
    version="1.0.0",
)

app.mount("/static", StaticFiles(directory=STATIC_DIR), name="static")

_EXAMPLE_REQUEST = os.path.abspath(
    os.path.join(os.path.dirname(__file__), "..", "example_request.json")
)


@app.get("/")
def read_root():
    return RedirectResponse(url="/ui", status_code=302)


@app.get("/ui")
def demo_ui():
    return FileResponse(os.path.join(STATIC_DIR, "index.html"))


@app.get("/example_request.json")
def example_request():
    if not os.path.isfile(_EXAMPLE_REQUEST):
        raise HTTPException(status_code=404, detail="example_request.json not found")
    return FileResponse(_EXAMPLE_REQUEST, media_type="application/json")


@app.get("/api")
def api_index():
    return {
        "message": "Bulk Certificate Generator API",
        "version": "1.0.0",
        "demo_ui": "/ui",
        "docs": "/docs",
        "endpoints": {
            "POST /jobs": "Create a new certificate generation job",
            "GET /jobs/{job_id}": "Get job status and details",
            "GET /jobs/{job_id}/status": "Get job status only",
            "GET /jobs/{job_id}/certificates": "Get all certificates for a job",
            "GET /certificates/{certificate_id}": "Get a specific certificate",
            "GET /certificates/{certificate_id}/download": "Download certificate PDF",
        },
    }


@app.post("/jobs", response_model=JobStatusResponse, status_code=status.HTTP_201_CREATED)
def create_job(job_data: JobCreate, db: Session = Depends(get_db)):
    """
    Create a new certificate generation job.
    
    Accepts a list of recipients and initiates background processing
    to generate certificates for each recipient.
    """
    # Validate recipients
    if not job_data.recipients:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="At least one recipient is required"
        )
    
    # Create job
    job = Job(
        status=JobStatus.PENDING,
        total_recipients=len(job_data.recipients)
    )
    db.add(job)
    db.commit()
    db.refresh(job)
    
    # Create certificate records for each recipient
    for recipient in job_data.recipients:
        certificate = Certificate(
            job_id=job.id,
            recipient_name=recipient.name,
            recipient_email=recipient.email,
            course_name=recipient.course_name,
            completion_date=recipient.completion_date
        )
        db.add(certificate)
    
    db.commit()
    
    # Trigger background processing
    process_certificate_generation.delay(job.id)
    
    return job


@app.get("/jobs/{job_id}", response_model=JobResponse)
def get_job(job_id: int, db: Session = Depends(get_db)):
    """
    Get job details including all certificates.
    """
    job = db.query(Job).filter(Job.id == job_id).first()
    if not job:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Job {job_id} not found"
        )
    
    return job


@app.get("/jobs/{job_id}/status", response_model=JobStatusResponse)
def get_job_status(job_id: int, db: Session = Depends(get_db)):
    """
    Get job status without loading all certificates.
    Use this endpoint for polling job progress.
    """
    job = db.query(Job).filter(Job.id == job_id).first()
    if not job:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Job {job_id} not found"
        )
    
    return job


@app.get("/jobs/{job_id}/certificates")
def get_job_certificates(job_id: int, db: Session = Depends(get_db)):
    """
    Get all certificates for a specific job.
    """
    job = db.query(Job).filter(Job.id == job_id).first()
    if not job:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Job {job_id} not found"
        )
    
    certificates = db.query(Certificate).filter(Certificate.job_id == job_id).all()
    return certificates


@app.get("/certificates/{certificate_id}")
def get_certificate(certificate_id: int, db: Session = Depends(get_db)):
    """
    Get details of a specific certificate.
    """
    certificate = db.query(Certificate).filter(Certificate.id == certificate_id).first()
    if not certificate:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Certificate {certificate_id} not found"
        )
    
    return certificate


@app.get("/certificates/{certificate_id}/download")
def download_certificate(certificate_id: int, db: Session = Depends(get_db)):
    """
    Download the generated certificate PDF.
    """
    certificate = db.query(Certificate).filter(Certificate.id == certificate_id).first()
    if not certificate:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Certificate {certificate_id} not found"
        )
    
    if certificate.status.value != "success":
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Certificate generation {certificate.status.value}. Cannot download."
        )
    
    if not certificate.certificate_path or not os.path.exists(certificate.certificate_path):
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Certificate file not found"
        )
    
    filename = os.path.basename(certificate.certificate_path)
    return FileResponse(
        certificate.certificate_path,
        media_type="application/pdf",
        filename=filename
    )


@app.get("/jobs")
def list_jobs(skip: int = 0, limit: int = 100, db: Session = Depends(get_db)):
    """
    List all jobs with pagination.
    """
    jobs = db.query(Job).offset(skip).limit(limit).all()
    return jobs
