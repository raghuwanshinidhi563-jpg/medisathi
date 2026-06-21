from django.shortcuts import render
from django.conf import settings
from .models import MedicalReport
from groq import Groq
import pytesseract
import os
import pyttsx3
from io import BytesIO
import base64

client = Groq(api_key=os.getenv('GROQ_API_KEY'))

pytesseract.pytesseract.tesseract_cmd = r'C:\Program Files\Tesseract-OCR\tesseract.exe'

# Language mappings
LANGUAGE_NAMES = {
    'english': 'English',
    'hindi': 'Hindi',
    'marathi': 'Marathi',
    'bengali': 'Bengali',
    'tamil': 'Tamil',
    'telugu': 'Telugu'
}

def get_risk_category(explanation):
    explanation_lower = explanation.lower()
    if any(word in explanation_lower for word in ['critical', 'urgent', 'immediately', 'dangerous', 'severe', 'जरूरी', 'गंभीर', 'तत्काल']):
        return 'red'
    elif any(word in explanation_lower for word in ['consult', 'doctor', 'monitor', 'slightly', 'low', 'high', 'मिलें', 'करें', 'सलाह']):
        return 'yellow'
    else:
        return 'green'

def generate_audio_explanation(text, language='english'):
    """Generate audio from text using text-to-speech"""
    try:
        engine = pyttsx3.init()
        
        # Set language-specific voice properties
        if language == 'hindi':
            engine.setProperty('rate', 150)  # Slower for clarity
        else:
            engine.setProperty('rate', 150)
        
        # Save audio to BytesIO instead of file
        audio_file = BytesIO()
        engine.save_to_file(text, 'temp_audio.mp3')
        engine.runAndWait()
        
        # Read the generated file and convert to base64
        try:
            with open('temp_audio.mp3', 'rb') as f:
                audio_data = f.read()
                audio_base64 = base64.b64encode(audio_data).decode()
            os.remove('temp_audio.mp3')
            return audio_base64
        except:
            return None
    except Exception as e:
        print(f"Audio generation error: {e}")
        return None

def split_explanation_and_remedies(full_text):
    """Split the response into explanation and remedies"""
    # Look for the remedies section marker
    if "HOME REMEDIES:" in full_text or "होम रेमेडीज:" in full_text or "HOME REMEDY:" in full_text:
        # Split by the marker
        parts = full_text.split("HOME REMEDIES:", 1) or full_text.split("होम रेमेडीज:", 1) or full_text.split("HOME REMEDY:", 1)
        if len(parts) == 2:
            explanation = parts[0].strip()
            remedies = parts[1].strip()
            return explanation, remedies
    
    # If no marker found, return the full text as explanation and empty remedies
    return full_text, "Remedies will be suggested by the AI based on your report."

def home(request):
    return render(request, 'reports/home.html')

def upload_report(request):
    if request.method == 'POST':
        report_file = request.FILES.get('report')
        language = request.POST.get('language', 'english').lower()
        
        if not report_file:
            return render(request, 'reports/upload.html', {'error': 'Please upload a medical report image.'})
        
        if language not in LANGUAGE_NAMES:
            language = 'english'
        
        report = MedicalReport(selected_language=language)
        report.report_image = report_file
        report.save()
        
        try:
            image_path = os.path.join(settings.MEDIA_ROOT, str(report.report_image))
            extracted_text = pytesseract.image_to_string(image_path)
            
            if not extracted_text.strip():
                return render(request, 'reports/upload.html', 
                    {'error': 'Could not extract text from image. Please upload a clearer image.'})
            
            report.extracted_text = extracted_text
            
            # IMPROVED: Stronger language instruction for Groq
            language_name = LANGUAGE_NAMES.get(language, 'English')
            
            prompt = f"""You are MediSathi, an AI medical report interpreter for rural Indian communities.

IMPORTANT: Respond ONLY in {language_name} language. Every word must be in {language_name}. No English mixed.

Medical report text: {extracted_text}

Please provide response in EXACTLY this format:

[EXPLANATION SECTION]
1. Explain each medical parameter in simple, easy language that a farmer or rural person can understand
2. Mention what each value means for health
3. Suggest affordable Indian foods to eat if any deficiencies are found
4. State the risk level: GREEN (Safe) / YELLOW (See doctor soon) / RED (Urgent)
5. End with: "कृपया योग्य डॉक्टर से परामर्श लें" or equivalent in {language_name}

HOME REMEDIES:
Suggest 3-5 practical, affordable home remedies:
- Include Ayurvedic remedies, traditional Indian remedies, and wellness tips
- For each remedy: what it is, how to use it, benefits
- Use common local ingredients available in villages
- Make it simple for elderly people to understand

Response format:
- Keep sentences SHORT and SIMPLE
- Use common local language, not medical jargon
- Suggest LOCAL, AFFORDABLE foods and remedies
- Be encouraging but HONEST

CRITICAL: Entire response MUST be in {language_name} ONLY."""

            # Call Groq with improved model
            response = client.chat.completions.create(
                model=getattr(settings, 'GROQ_MODEL', 'llama-3.3-70b-versatile'),
                messages=[
                    {
                        "role": "system",
                        "content": f"You are MediSathi. Always respond in {language_name} language ONLY. Never use English."
                    },
                    {
                        "role": "user",
                        "content": prompt
                    }
                ],
                max_tokens=2000,
                temperature=0.7
            )
            
            full_response = response.choices[0].message.content
            
            # Split explanation and remedies
            explanation, remedies = split_explanation_and_remedies(full_response)
            
            report.ai_explanation = full_response  # Store the full response
            report.risk_category = get_risk_category(explanation)
            report.save()
            
            # Generate audio explanation
            audio_base64 = generate_audio_explanation(explanation, language)
            
            return render(request, 'reports/result.html', {
                'report': report,
                'explanation': explanation,
                'remedies': remedies,
                'risk': report.risk_category,
                'language': language_name,
                'audio_base64': audio_base64,
            })
            
        except Exception as e:
            print(f"Error processing report: {str(e)}")
            return render(request, 'reports/upload.html', {'error': f'Error: {str(e)}'})
    
    return render(request, 'reports/upload.html')

def history(request):
    reports = MedicalReport.objects.all().order_by('-created_at')[:10]
    return render(request, 'reports/history.html', {'reports': reports})