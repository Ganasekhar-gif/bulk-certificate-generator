from reportlab.lib.pagesizes import letter, landscape
from reportlab.lib import colors
from reportlab.platypus import SimpleDocTemplate, Paragraph, Spacer
from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
from reportlab.lib.units import inch
from reportlab.lib.enums import TA_CENTER
import os
from datetime import datetime, timezone
from typing import Tuple


class CertificateGenerator:
    def __init__(self, output_dir: str = "certificates"):
        self.output_dir = output_dir
        os.makedirs(self.output_dir, exist_ok=True)
    
    def generate_certificate(
        self,
        recipient_name: str,
        recipient_email: str,
        course_name: str,
        completion_date: str
    ) -> Tuple[str, str]:
        """
        Generate a certificate PDF for the given recipient.
        
        Returns:
            Tuple of (file_path, filename)
        """
        timestamp = datetime.now(timezone.utc).strftime("%Y%m%d_%H%M%S")
        safe_name = recipient_name.replace(" ", "_").replace("/", "_")
        filename = f"certificate_{safe_name}_{timestamp}.pdf"
        file_path = os.path.join(self.output_dir, filename)
        
        # Create PDF with landscape orientation
        doc = SimpleDocTemplate(
            file_path,
            pagesize=landscape(letter),
            rightMargin=72,
            leftMargin=72,
            topMargin=72,
            bottomMargin=72
        )
        
        # Build certificate content
        story = []
        styles = getSampleStyleSheet()
        
        # Custom styles
        title_style = ParagraphStyle(
            'CustomTitle',
            parent=styles['Heading1'],
            fontSize=36,
            textColor=colors.darkblue,
            alignment=TA_CENTER,
            spaceAfter=30
        )
        
        subtitle_style = ParagraphStyle(
            'CustomSubtitle',
            parent=styles['Heading2'],
            fontSize=24,
            textColor=colors.black,
            alignment=TA_CENTER,
            spaceAfter=20
        )
        
        body_style = ParagraphStyle(
            'CustomBody',
            parent=styles['Normal'],
            fontSize=18,
            textColor=colors.black,
            alignment=TA_CENTER,
            spaceAfter=15
        )
        
        name_style = ParagraphStyle(
            'CustomName',
            parent=styles['Heading2'],
            fontSize=28,
            textColor=colors.darkgreen,
            alignment=TA_CENTER,
            spaceAfter=30
        )
        
        # Certificate title
        story.append(Paragraph("Certificate of Completion", title_style))
        story.append(Spacer(1, 0.3 * inch))
        
        # This is to certify that
        story.append(Paragraph("This is to certify that", body_style))
        story.append(Spacer(1, 0.2 * inch))
        
        # Recipient name
        story.append(Paragraph(recipient_name, name_style))
        story.append(Spacer(1, 0.3 * inch))
        
        # Has successfully completed
        story.append(Paragraph("has successfully completed the course", body_style))
        story.append(Spacer(1, 0.2 * inch))
        
        # Course name
        story.append(Paragraph(course_name, subtitle_style))
        story.append(Spacer(1, 0.3 * inch))
        
        # Completion date
        story.append(Paragraph(f"on {completion_date}", body_style))
        story.append(Spacer(1, 0.5 * inch))
        
        # Add decorative border
        story.append(Spacer(1, 0.2 * inch))
        
        # Build PDF
        doc.build(story)
        
        return file_path, filename
    
    def add_border(self, canvas_obj, width, height):
        """Add a decorative border to the certificate."""
        canvas_obj.setStrokeColor(colors.darkblue)
        canvas_obj.setLineWidth(3)
        canvas_obj.rect(50, 50, width - 100, height - 100)
        
        canvas_obj.setStrokeColor(colors.gold)
        canvas_obj.setLineWidth(1)
        canvas_obj.rect(55, 55, width - 110, height - 110)
