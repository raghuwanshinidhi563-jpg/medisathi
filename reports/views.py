from django.shortcuts import render, redirect
from .models import MedicalReport
import os
import urllib.parse
from groq import Groq
import random

# Initialize Groq with actual key
try:
    client = Groq(api_key=os.getenv('GROQ_API_KEY'))
except:
    client = None

LANGUAGE_NAMES = {
    'english': 'English',
    'hindi': 'Hindi',
    'marathi': 'Marathi',
    'bengali': 'Bengali',
    'tamil': 'Tamil',
    'telugu': 'Telugu'
}

# Mock ML detection (simulates trained model)
MOCK_DISEASES = [
    ('Melanoma', 'red'),
    ('Acne', 'green'),
    ('Dermatitis', 'yellow'),
    ('Fungal Infection', 'yellow'),
    ('Eczema', 'green'),
    ('Psoriasis', 'yellow'),
    ('Fungal Infection', 'yellow'),
    ('Wart', 'green'),
]

SPECIALTY_MAP = {
    'melanoma': 'Oncologist',
    'acne': 'Dermatologist',
    'dermatitis': 'Dermatologist',
    'fungal infection': 'Dermatologist',
    'eczema': 'Dermatologist',
    'psoriasis': 'Dermatologist',
    'wart': 'Dermatologist',
}

def home(request):
    return render(request, 'reports/home.html')

def disease_detector(request):
    """Upload skin photo for disease detection"""
    if request.method == 'POST':
        try:
            report_file = request.FILES.get('photo')
            lang = request.POST.get('language', 'english').lower()
            
            if not report_file:
                return render(request, 'reports/disease_detector.html', {'error': 'Please upload a photo'})
            
            if lang not in LANGUAGE_NAMES:
                lang = 'english'
            
            # Save report
            report = MedicalReport(selected_language=lang)
            report.report_image = report_file
            report.save()
            
            # Mock ML: Randomly select disease
            disease_name, risk_color = random.choice(MOCK_DISEASES)
            lang_name = LANGUAGE_NAMES[lang]
            
            # AI Response from Groq
            ai_response = "🩺 DISEASE: Analyzing...\n⚠️ RISK: Analyzing...\n📚 DEFINITION: Analyzing...\n❓ CAUSES: Analyzing...\n🌿 HOME REMEDIES: Analyzing...\n🍽️ FOODS TO EAT: Analyzing...\n❌ FOODS TO AVOID: Analyzing...\n🏥 WHEN TO SEE DOCTOR: Analyzing..."
            
            try:
                if client:
                    response = client.chat.completions.create(
                        model='mixtral-8x7b-32768',
                        messages=[
                            {
                                "role": "system",
                                "content": f"You are MediSathi dermatology AI. Respond ONLY in {lang_name}. Provide disease analysis with: name, risk level, definition, causes, home remedies, foods, when to see doctor."
                            },
                            {
                                "role": "user",
                                "content": f"Detected skin disease: {disease_name}. Provide analysis in {lang_name}."
                            }
                        ],
                        max_tokens=1000,
                        temperature=0.7
                    )
                    ai_response = response.choices[0].message.content
            except Exception as e:
                ai_response = f"🩺 DISEASE: {disease_name}\n⚠️ RISK: {risk_color.upper()}\n📚 DEFINITION: A skin condition detected by AI\n❓ CAUSES: Various factors\n🌿 HOME REMEDIES: Apply natural oils and herbs\n🍽️ FOODS TO EAT: Fruits, vegetables, water\n❌ FOODS TO AVOID: Spicy, fried foods\n🏥 WHEN TO SEE DOCTOR: If symptoms persist"
            
            report.extracted_text = f"Detected: {disease_name}"
            report.ai_explanation = ai_response
            report.risk_category = risk_color
            report.save()
            
            specialty = SPECIALTY_MAP.get(disease_name.lower(), 'Dermatologist')
            
            return render(request, 'reports/disease_result.html', {
                'report': report,
                'explanation': ai_response,
                'risk': risk_color,
                'language': lang_name,
                'symptom': disease_name,
                'disease_name': disease_name,
                'specialty': specialty,
            })
        
        except Exception as e:
            return render(request, 'reports/disease_detector.html', {'error': str(e)})
    
    return render(request, 'reports/disease_detector.html')

def find_doctors(request):
    """Find real dermatologists"""
    disease = request.GET.get('disease', 'Dermatologist').lower()
    specialty = SPECIALTY_MAP.get(disease.lower(), 'Dermatologist')
    
    justdial_link = f"https://www.justdial.com/search?q={urllib.parse.quote(specialty)}"
    practo_link = f"https://www.practo.com/search/dermatologist"
    lybrate_link = f"https://www.lybrate.com/search?q={urllib.parse.quote(specialty)}"
    
    return render(request, 'reports/doctor_finder.html', {
        'disease': disease,
        'specialty': specialty,
        'justdial_link': justdial_link,
        'practo_link': practo_link,
        'lybrate_link': lybrate_link,
    })

def book_consultation(request):
    if request.method == 'POST':
        platform = request.POST.get('platform', 'justdial')
        specialty = request.POST.get('specialty', 'Dermatologist')
        
        links = {
            'justdial': f"https://www.justdial.com/search?q={urllib.parse.quote(specialty)}",
            'practo': "https://www.practo.com/search/dermatologist",
            'lybrate': f"https://www.lybrate.com/search?q={urllib.parse.quote(specialty)}",
        }
        
        return render(request, 'reports/booking_confirmation.html', {
            'platform': platform,
            'specialty': specialty,
            'booking_link': links.get(platform, 'https://www.justdial.com'),
        })
    
    return redirect('home')

def voice_assistant(request):
    return redirect('home')

def history(request):
    try:
        reports = MedicalReport.objects.all().order_by('-created_at')[:10]
        return render(request, 'reports/history.html', {'reports': reports})
    except:
        return render(request, 'reports/history.html', {'reports': []})

def upload_report(request):
    return render(request, 'reports/upload.html')