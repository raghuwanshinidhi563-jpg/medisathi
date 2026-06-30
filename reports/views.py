from django.shortcuts import render
from django.conf import settings
from .models import MedicalReport
from groq import Groq
import requests
import os
from io import BytesIO

client = Groq(api_key=os.getenv('GROQ_API_KEY'))

LANGUAGE_NAMES = {
    'english': 'English',
    'hindi': 'Hindi',
    'marathi': 'Marathi',
    'bengali': 'Bengali',
    'tamil': 'Tamil',
    'telugu': 'Telugu'
}

def extract_text_easyapi(image_file):
    """Extract text using OCR.Space API - COMPLETELY FREE"""
    try:
        # Read image data
        image_data = image_file.read()
        image_file.seek(0)  # Reset file pointer
        
        # Send to OCR.Space API
        url = 'https://api.ocr.space/parse/image'
        payload = {
            'apikey': 'K87899142372222',
            'language': 'eng',
        }
        
        files = {'filename': image_data}
        
        response = requests.post(url, data=payload, files=files, timeout=30)
        result = response.json()
        
        if result.get('IsErroredOnProcessing') == False:
            text = result.get('ParsedText', '').strip()
            if text and len(text) > 20:
                return text
        
        return None
    except Exception as e:
        print(f"OCR Error: {e}")
        return None

def get_risk_category(text):
    t = (text or '').lower()
    if any(w in t for w in ['critical', 'urgent', 'severe', 'red']): 
        return 'red'
    if any(w in t for w in ['yellow', 'consult', 'doctor', 'soon']): 
        return 'yellow'
    return 'green'

def home(request):
    return render(request, 'reports/home.html')

def upload_report(request):
    if request.method == 'POST':
        try:
            report_file = request.FILES.get('report')
            lang = request.POST.get('language', 'english').lower()
            
            if not report_file:
                return render(request, 'reports/upload.html', {'error': 'Please upload a medical report image'})
            
            if lang not in LANGUAGE_NAMES:
                lang = 'english'
            
            # Show processing message
            print(f"Processing image: {report_file.name}")
            
            # Extract text using OCR.Space API
            extracted_text = extract_text_easyapi(report_file)
            
            if not extracted_text:
                return render(request, 'reports/upload.html', 
                    {'error': 'Could not read the image. Please upload a CLEAR, well-lit photo of your medical report. Make sure text is readable.'})
            
            print(f"Extracted text: {extracted_text[:100]}")
            
            # Save report
            report = MedicalReport(selected_language=lang)
            report.report_image = report_file
            report.extracted_text = extracted_text
            report.save()
            print(f"Report saved: {report.id}")
            
            lang_name = LANGUAGE_NAMES[lang]
            
            try:
                print("Calling Groq API...")
                # Send to Groq for analysis
                response = client.chat.completions.create(
                    model='llama-3.3-70b-versatile',
                    messages=[
                        {
                            "role": "system",
                            "content": f"""You are MediSathi, a medical report analyzer for Indian patients. 
Respond ONLY in {lang_name} language. NEVER use English.

For EACH medical parameter in the patient's report:
- Show normal range
- Show their value
- Say if HIGH/LOW/NORMAL
- Explain what it means (short + long)
- Explain why it's like that
- How to fix it (foods, actions)
- What to avoid
- Risk level (GREEN/YELLOW/RED)

Be detailed, helpful, and practical."""
                        },
                        {
                            "role": "user",
                            "content": f"""Patient's Medical Report Values (extracted from image):

{extracted_text}

Please analyze EACH parameter shown in this report. For every value, provide:

[PARAMETER NAME]
Normal: [range]
Your Value: [value]  
Status: [HIGH/LOW/NORMAL]

📚 What is it?
[Simple 1-2 line definition]

📖 How it affects you:
[3-4 lines explaining effects on body]

❓ Why is yours [LOW/HIGH]?
[2-3 lines on causes/reasons]

✅ How to Fix:
- Food 1: [benefit]
- Food 2: [benefit]  
- Action 1: [benefit]

❌ Avoid:
- Food 1 [why]
- Habit 1 [why]

⏱️ Timeline: [Recovery time]

Risk: [GREEN/YELLOW/RED]

---

Then provide:

OVERALL RISK: [GREEN/YELLOW/RED]

HOME REMEDIES:
[Specific remedies for THEIR values]

SUMMARY:
[Overall health status]

RESPOND ONLY IN {lang_name}. NO ENGLISH."""
                        }
                    ],
                    max_tokens=3500,
                    temperature=0.7
                )
                
                print("Groq response received")
                result = response.choices[0].message.content
                
                # Split explanation and remedies
                if "HOME REMEDIES" in result:
                    parts = result.split("HOME REMEDIES", 1)
                    explanation = parts[0].strip()
                    remedies = "HOME REMEDIES" + parts[1]
                else:
                    explanation = result
                    remedies = "Please consult a qualified doctor."
                
                report.ai_explanation = result
                report.risk_category = get_risk_category(explanation)
                report.save()
                print("Analysis complete")
                
                return render(request, 'reports/result.html', {
                    'report': report,
                    'explanation': explanation.strip(),
                    'remedies': remedies.strip(),
                    'risk': report.risk_category,
                    'language': lang_name,
                })
            
            except Exception as api_error:
                print(f"Groq API Error: {api_error}")
                return render(request, 'reports/upload.html', {'error': f'Analysis error: {str(api_error)}'})
        
        except Exception as e:
            print(f"General Error: {e}")
            return render(request, 'reports/upload.html', {'error': f'Error: {str(e)}'})
    
    return render(request, 'reports/upload.html')

def history(request):
    try:
        reports = MedicalReport.objects.all().order_by('-created_at')[:10]
        return render(request, 'reports/history.html', {'reports': reports})
    except:
        return render(request, 'reports/history.html', {'reports': []})