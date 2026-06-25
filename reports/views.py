from django.shortcuts import render
from .models import MedicalReport
from groq import Groq
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
    if any(w in t for w in ['critical', 'urgent', 'severe', 'immediately']): 
        return 'red'
    if any(w in t for w in ['consult', 'doctor', 'monitor', 'soon']): 
        return 'yellow'
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
                return render(request, 'reports/upload.html', {'error': 'Please enter valid report text (minimum 5 characters)'})
            
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
                        {
                            "role": "system",
                            "content": f"You are MediSathi, a helpful medical report interpreter for Indian communities. You MUST respond ONLY in {lang_name} language. ALWAYS include a HOME REMEDIES: section with practical, affordable remedies."
                        },
                        {
                            "role": "user",
                            "content": f"""Medical report text:
{text}

IMPORTANT - Please respond in this EXACT format in {lang_name} language:

EXPLANATION:
- Explain each medical parameter in simple language that anyone can understand
- Say what each value means for health
- Mention if values are normal, low, or high
- Suggest affordable Indian foods if deficiencies are found
- State the risk level: GREEN (Safe) / YELLOW (Consult doctor soon) / RED (Urgent medical attention needed)

HOME REMEDIES:
- List 3-5 practical, affordable home remedies
- Include Ayurvedic remedies and traditional Indian solutions
- For each remedy, explain: what it is, how to use it, and the benefits
- Use common ingredients available in Indian markets/kitchens
- Make it easy for elderly or non-educated people to understand

Remember:
- Use simple {lang_name} language only
- No English words
- Suggest LOCAL, AFFORDABLE solutions
- Be honest about when to see a doctor"""
                        }
                    ],
                    max_tokens=2000,
                    temperature=0.7
                )
                
                result = response.choices[0].message.content
                
                # Split explanation and remedies
                if "HOME REMEDIES:" in result:
                    explanation, remedies = result.split("HOME REMEDIES:", 1)
                    remedies = "HOME REMEDIES:" + remedies
                elif "Home Remedies:" in result:
                    explanation, remedies = result.split("Home Remedies:", 1)
                    remedies = "Home Remedies:" + remedies
                elif "होम रेमेडीज:" in result:
                    explanation, remedies = result.split("होम रेमेडीज:", 1)
                    remedies = "होम रेमेडीज:" + remedies
                else:
                    explanation = result
                    remedies = "Please consult a qualified doctor for proper medical advice and treatment."
                
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
                error_msg = f'Error calling AI service: {str(api_error)}'
                print(error_msg)
                return render(request, 'reports/upload.html', {'error': error_msg})
        
        except Exception as e:
            error_msg = f'Error processing report: {str(e)}'
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