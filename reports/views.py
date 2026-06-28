from django.shortcuts import render
from django.conf import settings
from .models import MedicalReport
from groq import Groq
import os
import base64

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
            
            # Convert image to base64
            image_data = base64.b64encode(report_file.read()).decode('utf-8')
            
            # Save report
            report = MedicalReport(selected_language=lang)
            report.report_image = report_file
            report.save()
            
            lang_name = LANGUAGE_NAMES[lang]
            
            try:
                # Send image to Groq for analysis (with vision)
                response = client.chat.completions.create(
                    model='llama-3.3-70b-versatile',
                    messages=[
                        {
                            "role": "system",
                            "content": f"""You are MediSathi, a medical report analyzer. Respond ONLY in {lang_name}.
Analyze the medical report IMAGE provided.
For EACH parameter visible in the report:
1. Read the VALUE from the image
2. Compare with NORMAL range
3. Explain if HIGH/LOW/NORMAL
4. Explain effects on body
5. Suggest how to fix
6. Suggest what to avoid

Be detailed and personalized."""
                        },
                        {
                            "role": "user",
                            "content": [
                                {
                                    "type": "text",
                                    "text": f"""Please analyze this medical report image in {lang_name}.

For EACH parameter in the report:

[PARAMETER]
Normal Range: [what you see]
Your Value: [what you see]
Status: [HIGH/LOW/NORMAL]

📚 What is it?
[Brief definition]

📖 How it affects you:
[Detailed explanation]

❓ Why is yours this way?
[Causes/reasons]

✅ How to fix:
[Foods and actions]

❌ What to avoid:
[Foods and habits to avoid]

⏱️ Timeline: [Recovery time]

Risk: [GREEN/YELLOW/RED]

---

Then:
HOME REMEDIES:
[Specific remedies for their values]

SUMMARY:
[Overall health status]

Respond ONLY in {lang_name}"""
                                },
                                {
                                    "type": "image_url",
                                    "image_url": {
                                        "url": f"data:image/jpeg;base64,{image_data}"
                                    }
                                }
                            ]
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
                    remedies = "Please consult a doctor."
                
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
                error_msg = f'Error: {str(api_error)}'
                print(error_msg)
                return render(request, 'reports/upload.html', {'error': error_msg})
        
        except Exception as e:
            print(f'Error: {str(e)}')
            return render(request, 'reports/upload.html', {'error': str(e)})
    
    return render(request, 'reports/upload.html')

def history(request):
    try:
        reports = MedicalReport.objects.all().order_by('-created_at')[:10]
        return render(request, 'reports/history.html', {'reports': reports})
    except:
        return render(request, 'reports/history.html', {'reports': []})