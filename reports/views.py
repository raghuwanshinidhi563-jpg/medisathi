from django.shortcuts import render, redirect
from .models import MedicalReport
import os
import urllib.parse
from groq import Groq

# Don't initialize here - do it in each function

LANGUAGE_NAMES = {
    'english': 'English',
    'hindi': 'Hindi',
    'marathi': 'Marathi',
    'bengali': 'Bengali',
    'tamil': 'Tamil',
    'telugu': 'Telugu'
}

SPECIALTY_MAP = {
    'headache': 'Neurologist',
    'migraine': 'Neurologist',
    'fever': 'General Physician',
    'cough': 'General Physician',
    'cold': 'General Physician',
    'acne': 'Dermatologist',
    'fungal infection': 'Dermatologist',
    'skin rash': 'Dermatologist',
    'eczema': 'Dermatologist',
    'psoriasis': 'Dermatologist',
    'urticaria': 'Dermatologist',
    'wound': 'General Physician',
    'burn': 'General Physician',
    'stomachache': 'General Physician',
    'diarrhea': 'General Physician',
    'allergy': 'General Physician',
    'asthma': 'General Physician',
    'eye problem': 'General Physician',
    'toothache': 'General Physician',
    'hair loss': 'Dermatologist',
    'fatigue': 'General Physician',
    'chest pain': 'Cardiologist',
    'high blood pressure': 'Cardiologist',
    'diabetes': 'General Physician',
    'joint pain': 'General Physician',
    'back pain': 'General Physician',
}

def get_risk_category(text):
    t = (text or '').lower()
    if any(w in t for w in ['critical', 'urgent', 'severe', 'emergency']): 
        return 'red'
    if any(w in t for w in ['consult', 'doctor', 'soon', 'concerning']): 
        return 'yellow'
    return 'green'

def home(request):
    return render(request, 'reports/home.html')

def disease_detector(request):
    """Upload photo for disease detection"""
    if request.method == 'POST':
        try:
            report_file = request.FILES.get('photo')
            lang = request.POST.get('language', 'english').lower()
            
            if not report_file:
                return render(request, 'reports/disease_detector.html', {'error': 'Please upload a photo'})
            
            if lang not in LANGUAGE_NAMES:
                lang = 'english'
            
            disease_description = request.POST.get('description', '').strip()
            
            if not disease_description:
                return render(request, 'reports/disease_detector.html', {'error': 'Please describe your symptom'})
            
            report = MedicalReport(selected_language=lang)
            report.report_image = report_file
            report.extracted_text = disease_description
            report.save()
            
            lang_name = LANGUAGE_NAMES[lang]
            
            try:
                # Initialize Groq HERE, not at top level
                client = Groq(api_key=os.getenv('GROQ_API_KEY'))
                
                response = client.chat.completions.create(
                    model='llama-3.3-70b-versatile',
                    messages=[
                        {
                            "role": "system",
                            "content": f"""You are MediSathi, a medical symptom analyzer. Respond ONLY in {lang_name}.
Analyze the symptom and provide:
1. Likely disease name
2. Risk level (GREEN/YELLOW/RED)
3. Definition
4. Causes
5. Home remedies
6. Foods to eat
7. Foods to avoid
8. When to see doctor"""
                        },
                        {
                            "role": "user",
                            "content": f"""Symptom: {disease_description}

Provide in {lang_name}:
🩺 DISEASE:
⚠️ RISK:
📚 DEFINITION:
❓ CAUSES:
🌿 HOME REMEDIES:
🍽️ FOODS TO EAT:
❌ FOODS TO AVOID:
🏥 WHEN TO SEE DOCTOR:"""
                        }
                    ],
                    max_tokens=2000,
                    temperature=0.7
                )
                
                result = response.choices[0].message.content
                report.ai_explanation = result
                report.risk_category = get_risk_category(result)
                report.save()
                
                disease_name = disease_description.lower()
                
                return render(request, 'reports/disease_result.html', {
                    'report': report,
                    'explanation': result.strip(),
                    'risk': report.risk_category,
                    'language': lang_name,
                    'symptom': disease_description,
                    'disease_name': disease_name,
                })
            
            except Exception as api_error:
                return render(request, 'reports/disease_detector.html', {'error': f'Error: {str(api_error)}'})
        
        except Exception as e:
            return render(request, 'reports/disease_detector.html', {'error': str(e)})
    
    return render(request, 'reports/disease_detector.html')

def find_doctors(request):
    """Find real doctors - redirect to booking platforms"""
    disease = request.GET.get('disease', 'doctor').lower()
    location = request.GET.get('location', 'India').lower()
    
    specialty = SPECIALTY_MAP.get(disease.lower(), 'Doctor')
    
    search_query = f"{specialty} for {disease}"
    
    justdial_link = f"https://www.justdial.com/search?q={urllib.parse.quote(specialty)}"
    practo_link = f"https://www.practo.com/search/general_physician"
    lybrate_link = f"https://www.lybrate.com/search?q={urllib.parse.quote(specialty)}"
    
    return render(request, 'reports/doctor_finder.html', {
        'disease': disease,
        'specialty': specialty,
        'location': location,
        'justdial_link': justdial_link,
        'practo_link': practo_link,
        'lybrate_link': lybrate_link,
    })

def book_consultation(request):
    """Redirect to booking platform"""
    if request.method == 'POST':
        platform = request.POST.get('platform', 'justdial')
        specialty = request.POST.get('specialty', 'doctor')
        
        if platform == 'justdial':
            link = f"https://www.justdial.com/search?q={urllib.parse.quote(specialty)}"
        elif platform == 'practo':
            link = f"https://www.practo.com/search/general_physician"
        elif platform == 'lybrate':
            link = f"https://www.lybrate.com/search?q={urllib.parse.quote(specialty)}"
        else:
            link = 'https://www.justdial.com'
        
        return render(request, 'reports/booking_confirmation.html', {
            'platform': platform,
            'specialty': specialty,
            'booking_link': link,
        })
    
    return redirect('home')

def voice_assistant(request):
    """Voice Health Assistant - Text input"""
    if request.method == 'POST':
        try:
            symptom_text = request.POST.get('symptoms', '').strip()
            lang = request.POST.get('language', 'english').lower()
            
            if not symptom_text:
                return render(request, 'reports/voice.html', {'error': 'Please type your symptoms'})
            
            if lang not in LANGUAGE_NAMES:
                lang = 'english'
            
            lang_name = LANGUAGE_NAMES[lang]
            
            report = MedicalReport(selected_language=lang)
            report.extracted_text = symptom_text
            report.save()
            
            try:
                # Initialize Groq HERE
                client = Groq(api_key=os.getenv('GROQ_API_KEY'))
                
                response = client.chat.completions.create(
                    model='llama-3.3-70b-versatile',
                    messages=[
                        {
                            "role": "system",
                            "content": f"You are MediSathi health assistant. Respond ONLY in {lang_name}."
                        },
                        {
                            "role": "user",
                            "content": f"""Symptoms: {symptom_text}

Provide in {lang_name}:
🩺 What is it?
⚠️ Risk Level?
🌿 Home Remedies?
🍽️ Foods to Eat?
❌ Foods to Avoid?
🏥 When to See Doctor?"""
                        }
                    ],
                    max_tokens=1500,
                    temperature=0.7
                )
                
                result = response.choices[0].message.content
                report.ai_explanation = result
                report.risk_category = get_risk_category(result)
                report.save()
                
                return render(request, 'reports/voice_result.html', {
                    'report': report,
                    'explanation': result.strip(),
                    'risk': report.risk_category,
                    'language': lang_name,
                    'symptoms': symptom_text,
                })
            
            except Exception as api_error:
                return render(request, 'reports/voice.html', {'error': f'Error: {str(api_error)}'})
        
        except Exception as e:
            return render(request, 'reports/voice.html', {'error': str(e)})
    
    return render(request, 'reports/voice.html')

def history(request):
    try:
        reports = MedicalReport.objects.all().order_by('-created_at')[:10]
        return render(request, 'reports/history.html', {'reports': reports})
    except:
        return render(request, 'reports/history.html', {'reports': []})

def upload_report(request):
    return render(request, 'reports/upload.html')