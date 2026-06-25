from django.shortcuts import render
from .models import MedicalReport
from groq import Groq
import os

client = Groq(api_key=os.getenv('GROQ_API_KEY'))

LANGUAGE_NAMES = {'english': 'English', 'hindi': 'Hindi', 'marathi': 'Marathi', 'bengali': 'Bengali', 'tamil': 'Tamil', 'telugu': 'Telugu'}

def get_risk_category(text):
    t = (text or '').lower()
    if any(w in t for w in ['critical', 'urgent', 'severe']): return 'red'
    if any(w in t for w in ['consult', 'doctor', 'monitor']): return 'yellow'
    return 'green'

def home(request):
    return render(request, 'reports/home.html')

def upload_report(request):
    if request.method == 'POST':
        try:
            text = request.POST.get('extracted_text', '').strip()
            lang = request.POST.get('language', 'english').lower()
            
            if not text:
                return render(request, 'reports/upload.html', {'error': 'Please enter medical report text'})
            
            if len(text) < 5:
                return render(request, 'reports/upload.html', {'error': 'Please enter valid report text'})
            
            if lang not in LANGUAGE_NAMES:
                lang = 'english'
            
            report = MedicalReport(selected_language=lang)
            report.extracted_text = text
            report.save()
            
            lang_name = LANGUAGE_NAMES[lang]
            
            try:
                response = client.chat.completions.create(
                    model='llama-3.3-70b-versatile',
                    messages=[
                        {"role": "system", "content": f"You are MediSathi. Respond in {lang_name} only."},
                        {"role": "user", "content": f"Medical report:\n{text}\n\nExplain each parameter simply. Then list HOME REMEDIES:"}
                    ],
                    max_tokens=1500,
                    temperature=0.7
                )
                
                result = response.choices[0].message.content
                
                if "HOME REMEDIES:" in result:
                    explanation, remedies = result.split("HOME REMEDIES:", 1)
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
                return render(request, 'reports/upload.html', {'error': f'API Error: {str(api_error)}'})
        
        except Exception as e:
            return render(request, 'reports/upload.html', {'error': f'Error: {str(e)}'})
    
    return render(request, 'reports/upload.html')

def history(request):
    try:
        reports = MedicalReport.objects.all().order_by('-created_at')[:10]
        return render(request, 'reports/history.html', {'reports': reports})
    except:
        return render(request, 'reports/history.html', {'reports': []})