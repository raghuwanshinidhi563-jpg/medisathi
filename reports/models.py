from django.db import models

class MedicalReport(models.Model):
    LANGUAGE_CHOICES = [
        ('english', 'English'),
        ('hindi', 'Hindi'),
        ('marathi', 'Marathi'),
        ('bengali', 'Bengali'),
        ('tamil', 'Tamil'),
        ('telugu', 'Telugu'),
    ]
    
    selected_language = models.CharField(max_length=20, choices=LANGUAGE_CHOICES, default='english')
    extracted_text = models.TextField(blank=True)
    ai_explanation = models.TextField(blank=True)
    risk_category = models.CharField(max_length=10, default='green')
    created_at = models.DateTimeField(auto_now_add=True)
    
    class Meta:
        ordering = ['-created_at']
    
    def __str__(self):
        return f"Report - {self.created_at}"