from django.db import models

class MedicalReport(models.Model):
    RISK_CHOICES = [
        ('green', 'Routine Monitoring'),
        ('yellow', 'Consult Doctor Soon'),
        ('red', 'Seek Medical Attention'),
    ]

    LANGUAGE_CHOICES = [
        ('english', 'English'),
        ('hindi', 'Hindi'),
        ('marathi', 'Marathi'),
        ('bengali', 'Bengali'),
        ('tamil', 'Tamil'),
        ('telugu', 'Telugu'),
    ]

    # Report Upload
    report_image = models.ImageField(
        upload_to='reports/', 
        null=True, 
        blank=True
    )
    
    # Extracted Text
    extracted_text = models.TextField(null=True, blank=True)
    
    # AI Results
    ai_explanation = models.TextField(null=True, blank=True)
    risk_category = models.CharField(
        max_length=10, 
        choices=RISK_CHOICES, 
        null=True, 
        blank=True
    )
    
    # Language
    selected_language = models.CharField(
        max_length=20,
        choices=LANGUAGE_CHOICES,
        default='english'
    )
    
    # Timestamps
    uploaded_at = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return f"Report {self.id} - {self.uploaded_at.strftime('%d/%m/%Y')}"

    class Meta:
        ordering = ['-uploaded_at']
        verbose_name = 'Medical Report'
        verbose_name_plural = 'Medical Reports'
