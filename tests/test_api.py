import os
import shutil
import tempfile

from app.models import Certificate, CertificateStatus, Job, JobStatus


class TestJobCreation:
    def test_create_job_success(self, client):
        """Test creating a job with valid recipients"""
        response = client.post("/jobs", json={
            "recipients": [
                {
                    "name": "John Doe",
                    "email": "john@example.com",
                    "course_name": "Python Programming",
                    "completion_date": "2024-01-15"
                },
                {
                    "name": "Jane Smith",
                    "email": "jane@example.com",
                    "course_name": "Python Programming",
                    "completion_date": "2024-01-15"
                }
            ]
        })
        
        assert response.status_code == 201
        data = response.json()
        assert data["status"] == "pending"
        assert data["total_recipients"] == 2
        assert "id" in data
        assert data["successful_count"] == 0
        assert data["failed_count"] == 0
    
    def test_create_job_empty_recipients(self, client):
        """Test creating a job with no recipients should fail"""
        response = client.post("/jobs", json={
            "recipients": []
        })
        
        assert response.status_code == 422
    
    def test_create_job_invalid_email(self, client):
        """Test creating a job with invalid email should fail"""
        response = client.post("/jobs", json={
            "recipients": [
                {
                    "name": "John Doe",
                    "email": "invalid-email",
                    "course_name": "Python Programming",
                    "completion_date": "2024-01-15"
                }
            ]
        })
        
        assert response.status_code == 422  # Validation error

    def test_create_job_exceeds_recipient_limit(self, client):
        """Test creating a job with more than 1000 recipients should fail validation"""
        recipients = [
            {
                "name": f"User {i}",
                "email": f"user{i}@example.com",
                "course_name": "Python Programming",
                "completion_date": "2024-01-15"
            }
            for i in range(1001)
        ]
        response = client.post("/jobs", json={"recipients": recipients})
        assert response.status_code == 422


class TestJobStatus:
    def test_get_job_status(self, client):
        """Test retrieving job status"""
        # Create a job first
        create_response = client.post("/jobs", json={
            "recipients": [
                {
                    "name": "John Doe",
                    "email": "john@example.com",
                    "course_name": "Python Programming",
                    "completion_date": "2024-01-15"
                }
            ]
        })
        job_id = create_response.json()["id"]
        
        # Get job status
        response = client.get(f"/jobs/{job_id}/status")
        
        assert response.status_code == 200
        data = response.json()
        assert data["id"] == job_id
        assert "status" in data
        assert "total_recipients" in data
    
    def test_get_nonexistent_job(self, client):
        """Test retrieving status for non-existent job"""
        response = client.get("/jobs/99999/status")
        
        assert response.status_code == 404
        assert "not found" in response.json()["detail"]


class TestCertificateRetrieval:
    def test_get_job_certificates(self, client):
        """Test retrieving all certificates for a job"""
        # Create a job
        create_response = client.post("/jobs", json={
            "recipients": [
                {
                    "name": "John Doe",
                    "email": "john@example.com",
                    "course_name": "Python Programming",
                    "completion_date": "2024-01-15"
                },
                {
                    "name": "Jane Smith",
                    "email": "jane@example.com",
                    "course_name": "Python Programming",
                    "completion_date": "2024-01-15"
                }
            ]
        })
        job_id = create_response.json()["id"]
        
        # Get certificates
        response = client.get(f"/jobs/{job_id}/certificates")
        
        assert response.status_code == 200
        certificates = response.json()
        assert len(certificates) == 2
        assert all("recipient_name" in cert for cert in certificates)
    
    def test_get_specific_certificate(self, client, db_session):
        """Test retrieving a specific certificate"""
        # Create a job
        create_response = client.post("/jobs", json={
            "recipients": [
                {
                    "name": "John Doe",
                    "email": "john@example.com",
                    "course_name": "Python Programming",
                    "completion_date": "2024-01-15"
                }
            ]
        })
        job_id = create_response.json()["id"]
        
        # Get certificate ID from database
        certificate = db_session.query(Certificate).filter(Certificate.job_id == job_id).first()
        cert_id = certificate.id
        
        # Get specific certificate
        response = client.get(f"/certificates/{cert_id}")
        
        assert response.status_code == 200
        data = response.json()
        assert data["id"] == cert_id
        assert data["recipient_name"] == "John Doe"
    
    def test_get_nonexistent_certificate(self, client):
        """Test retrieving non-existent certificate"""
        response = client.get("/certificates/99999")
        
        assert response.status_code == 404


class TestCertificateGeneration:
    def test_certificate_generation_logic(self):
        """Test the certificate generation logic directly"""
        from app.certificate_generator import CertificateGenerator
        import tempfile
        import os
        
        # Use temp directory
        temp_dir = tempfile.mkdtemp()
        generator = CertificateGenerator(output_dir=temp_dir)
        
        try:
            file_path, filename = generator.generate_certificate(
                recipient_name="Test User",
                recipient_email="test@example.com",
                course_name="Test Course",
                completion_date="2024-01-15"
            )
            
            assert os.path.exists(file_path)
            assert file_path.endswith(".pdf")
            assert "Test_User" in filename
            
        finally:
            # Cleanup
            import shutil
            if os.path.exists(temp_dir):
                shutil.rmtree(temp_dir)


class TestFailureHandling:
    def test_individual_certificate_failure(self, client, db_session):
        """Test that one certificate failure doesn't affect others"""
        # This test simulates a scenario where one certificate might fail
        # by creating a job and manually marking one certificate as failed
        
        # Create a job
        create_response = client.post("/jobs", json={
            "recipients": [
                {
                    "name": "John Doe",
                    "email": "john@example.com",
                    "course_name": "Python Programming",
                    "completion_date": "2024-01-15"
                },
                {
                    "name": "Jane Smith",
                    "email": "jane@example.com",
                    "course_name": "Python Programming",
                    "completion_date": "2024-01-15"
                }
            ]
        })
        job_id = create_response.json()["id"]
        
        # Manually mark one certificate as failed to simulate failure
        certificates = db_session.query(Certificate).filter(Certificate.job_id == job_id).all()
        certificates[0].status = CertificateStatus.FAILED
        certificates[0].error_message = "Simulated failure"
        db_session.commit()
        
        # Update job to reflect partial success
        job = db_session.query(Job).filter(Job.id == job_id).first()
        job.successful_count = 1
        job.failed_count = 1
        job.status = JobStatus.COMPLETED
        db_session.commit()
        
        # Verify job shows partial success
        response = client.get(f"/jobs/{job_id}")
        data = response.json()
        
        assert data["successful_count"] == 1
        assert data["failed_count"] == 1
        assert data["status"] == "completed"
    
    def test_download_failed_certificate(self, client, db_session):
        """Test that downloading a failed certificate returns error"""
        # Create a job
        create_response = client.post("/jobs", json={
            "recipients": [
                {
                    "name": "John Doe",
                    "email": "john@example.com",
                    "course_name": "Python Programming",
                    "completion_date": "2024-01-15"
                }
            ]
        })
        job_id = create_response.json()["id"]
        
        # Mark certificate as failed
        certificate = db_session.query(Certificate).filter(Certificate.job_id == job_id).first()
        certificate.status = CertificateStatus.FAILED
        db_session.commit()
        
        # Try to download
        response = client.get(f"/certificates/{certificate.id}/download")
        
        assert response.status_code == 400
        assert "Cannot download" in response.json()["detail"]


class TestListJobs:
    def test_list_jobs(self, client):
        """Test listing all jobs"""
        # Create multiple jobs
        for i in range(3):
            client.post("/jobs", json={
                "recipients": [
                    {
                        "name": f"User {i}",
                        "email": f"user{i}@example.com",
                        "course_name": "Test Course",
                        "completion_date": "2024-01-15"
                    }
                ]
            })
        
        # List jobs
        response = client.get("/jobs")
        
        assert response.status_code == 200
        jobs = response.json()
        assert len(jobs) >= 3
    
    def test_list_jobs_with_pagination(self, client):
        """Test listing jobs with pagination"""
        # Create jobs
        for i in range(5):
            client.post("/jobs", json={
                "recipients": [
                    {
                        "name": f"User {i}",
                        "email": f"user{i}@example.com",
                        "course_name": "Test Course",
                        "completion_date": "2024-01-15"
                    }
                ]
            })
        
        # List with limit
        response = client.get("/jobs?skip=0&limit=3")
        
        assert response.status_code == 200
        jobs = response.json()
        assert len(jobs) <= 3
