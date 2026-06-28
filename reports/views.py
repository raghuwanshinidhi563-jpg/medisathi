from django.shortcuts import render
from django.conf import settings
from .models import MedicalReport
from groq import Groq
import requests
import os

client = Groq(api_key=os.getenv('GROQ_API_KEY'))

LANGUAGE_NAMES = {
    'english': 'English',
    'hindi': 'Hindi',
    'marathi': 'Marathi',
    'bengali': 'Bengali',
    'tamil': 'Tamil',
    'telugu': 'Telugu'
}

def get_risk_category(text):
    t = (text or '').lower()
    if any(w in t for w in ['critical', 'urgent', 'severe', 'red']): 
        return 'red'
    if any(w in t for w in ['yellow', 'consult', 'doctor', 'soon']): 
        return 'yellow'
    return 'green'

def extract_text_from_image(image_file):
    """Extract text using FREE OCR.space API"""
    try:
        files = {'filename': image_file}
        response = requests.post(
            'https://api.ocr.space/parse/image',
            files=files,
            data={'apikey': 'K87899142372222', 'language': 'eng'}
        )
        
        result = response.json()
        if result.get('IsErroredOnProcessing') == False:
            text = result.get('ParsedText', '').strip()
            return text if text else None
    except Exception as e:
        print(f"OCR Error: {e}")
    
    return None

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
            
            # Extract text from image
            extracted_text = extract_text_from_image(report_file)
            
            if not extracted_text or len(extracted_text.strip()) < 10:
                return render(request, 'reports/upload.html', 
                    {'error': 'Could not extract text from image. Please upload a clearer image with visible text.'})
            
            # Save report
            report = MedicalReport(selected_language=lang)
            report.report_image = report_file
            report.extracted_text = extracted_text
            report.save()
            
            lang_name = LANGUAGE_NAMES[lang]
            
            try:
                # Send to Groq for analysis
                response = client.chat.completions.create(
                    model='llama-3.3-70b-versatile',
                    messages=[
                        {
                            "role": "system",
                            "content": f"""You are MediSathi, a medical report analyzer. Respond ONLY in {lang_name}.
For EACH parameter in the patient's report, provide COMPLETE analysis with:
1. Normal range
2. Patient's actual value
3. Status (LOW/HIGH/NORMAL)
4. SHORT definition (what it is - 1-2 lines)
5. LONG explanation (how it affects body - detailed, 3-4 lines)
6. Why it's low/high (causes - 2-3 lines)
7. How to fix (foods, actions - specific)
8. What to avoid (foods, habits to avoid)
9. Risk level for this parameter
10. Time needed to improve

Be detailed, comprehensive, and personalized to their values."""
                        },
                        {
                            "role": "user",
                            "content": f"""Patient's Medical Report:
{extracted_text}

For EACH parameter in this report, provide detailed analysis in {lang_name}:

FORMAT:

[PARAMETER NAME]
━━━━━━━━━━━━━━━━
Normal Range: [healthy range]
Your Value: [their value]
Status: [LOW/HIGH/NORMAL]

📚 What is it? (Short definition)
[1-2 line definition]

📖 Detailed Explanation:
[3-4 lines explaining how this affects their body, what happens, symptoms]

❓ Why is yours [LOW/HIGH]?
[2-3 lines explaining causes/reasons specific to their value]

✅ How to Fix:
- Food 1: [benefit]
- Food 2: [benefit]
- Action 1: [benefit]
- Action 2: [benefit]

❌ What to Avoid:
- Avoid food 1 [why]
- Avoid habit 1 [why]
- Avoid food 2 [why]

⏱️ Timeline: [How long to improve]

Risk: [GREEN/YELLOW/RED]

---

Then provide:

OVERALL RISK LEVEL: [GREEN/YELLOW/RED based on all parameters]

HOME REMEDIES (Specific to their results):
[List remedies only for their specific problems]

SUMMARY:
[Brief summary of their health status]

IMPORTANT:
- Detailed analysis for EACH value
- Compare with normal ranges
- Explain effects on THEIR body
- Specific to their numbers
- Practical advice
- Respond ONLY in {lang_name}"""
                        }
                    ],
                    max_tokens=3500,
                    temperature=0.7
                )
                
                result = response.choices[0].message.content
                
                # Split explanation and remedies
                if "HOME REMEDIES" in result:
                    parts = result.split("HOME REMEDIES", 1)
                    explanation = parts[0].strip()
                    remedies = "HOME REMEDIES" + parts[1]
                else:
                    explanation = result
                    remedies = "Please consult a doctor for personalized medical advice."
                
                report.ai_explanation = result
                report.risk_category = get_risk_category(explanation)
                report.save()
                
                return render(request, 'reports/result.html', {
                    'report': report,
                    'explanation': explanation.strip(),
                    'remedies': remedies.strip(),
                    'risk': report.risk_category,
                    'language': lang_name,
                })
            
            except Exception as api_error:
                error_msg = f'Error analyzing report: {str(api_error)}'
                print(error_msg)
                return render(request, 'reports/upload.html', {'error': error_msg})
        
        except Exception as e:
            error_msg = f'Error processing: {str(e)}'
            print(error_msg)
            return render(request, 'reports/upload.html', {'error': error_msg})
    
    return render(request, 'reports/upload.html')

def history(request):
    try:
        reports = MedicalReport.objects.all().order_by('-created_at')[:10]
        return render(request, 'reports/history.html', {'reports': reports})
    except Exception as e:
        print(f'History error: {e}')
        return render(request, 'reports/history.html', {'reports': []})