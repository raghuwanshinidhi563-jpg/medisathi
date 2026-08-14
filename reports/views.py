from django.shortcuts import render, redirect
from django.http import JsonResponse
from .models import MedicalReport
from groq import Groq
import os
import json

client = Groq(api_key=os.getenv('GROQ_API_KEY'))

LANGUAGE_NAMES = {
    'english': 'English',
    'hindi': 'Hindi',
    'marathi': 'Marathi',
    'bengali': 'Bengali',
    'tamil': 'Tamil',
    'telugu': 'Telugu'
}

# Mock Online Doctors Database
ONLINE_DOCTORS = {
    'fungal infection': [
        {
            'name': 'Dr. Sharma',
            'specialty': 'Dermatologist',
            'hospital': 'Apollo Hospital',
            'city': 'Mumbai',
            'fees': 500,
            'duration': 30,
            'timing': 'Mon-Sat 10AM-6PM',
            'rating': 4.8,
            'experience': '15 years',
            'languages': ['English', 'Hindi', 'Marathi'],
            'availability': 'Available'
        },
        {
            'name': 'Dr. Patel',
            'specialty': 'Skin Specialist',
            'hospital': 'Max Healthcare',
            'city': 'Delhi',
            'fees': 400,
            'duration': 20,
            'timing': 'Daily 2PM-8PM',
            'rating': 4.6,
            'experience': '12 years',
            'languages': ['English', 'Hindi', 'Gujarati'],
            'availability': 'Available'
        },
        {
            'name': 'Dr. Malhotra',
            'specialty': 'Dermatologist',
            'hospital': 'Fortis Hospital',
            'city': 'Bangalore',
            'fees': 450,
            'duration': 25,
            'timing': 'Tue-Sun 11AM-7PM',
            'rating': 4.7,
            'experience': '10 years',
            'languages': ['English', 'Kannada', 'Hindi'],
            'availability': 'Available'
        }
    ],
    'acne': [
        {
            'name': 'Dr. Gupta',
            'specialty': 'Dermatologist',
            'hospital': 'Columbia Asia',
            'city': 'Pune',
            'fees': 350,
            'duration': 20,
            'timing': 'Mon-Sat 9AM-5PM',
            'rating': 4.5,
            'experience': '8 years',
            'languages': ['English', 'Hindi', 'Marathi'],
            'availability': 'Available'
        },
        {
            'name': 'Dr. Singh',
            'specialty': 'Skin Specialist',
            'hospital': 'Manipal Hospital',
            'city': 'Delhi',
            'fees': 400,
            'duration': 25,
            'timing': 'Daily 3PM-9PM',
            'rating': 4.7,
            'experience': '14 years',
            'languages': ['English', 'Hindi', 'Punjabi'],
            'availability': 'Available'
        }
    ],
    'eczema': [
        {
            'name': 'Dr. Verma',
            'specialty': 'Dermatologist',
            'hospital': 'Care Hospitals',
            'city': 'Hyderabad',
            'fees': 450,
            'duration': 30,
            'timing': 'Mon-Fri 10AM-6PM',
            'rating': 4.8,
            'experience': '16 years',
            'languages': ['English', 'Hindi', 'Telugu'],
            'availability': 'Available'
        },
        {
            'name': 'Dr. Kapoor',
            'specialty': 'Skin Specialist',
            'hospital': 'Lilavati Hospital',
            'city': 'Mumbai',
            'fees': 500,
            'duration': 30,
            'timing': 'Tue-Sat 2PM-8PM',
            'rating': 4.9,
            'experience': '18 years',
            'languages': ['English', 'Hindi', 'Marathi', 'Gujarati'],
            'availability': 'Available'
        }
    ],
    'urticaria': [
        {
            'name': 'Dr. Nair',
            'specialty': 'Allergist & Dermatologist',
            'hospital': 'Amrita Hospital',
            'city': 'Kochi',
            'fees': 400,
            'duration': 25,
            'timing': 'Mon-Sun 9AM-7PM',
            'rating': 4.6,
            'experience': '11 years',
            'languages': ['English', 'Hindi', 'Malayalam'],
            'availability': 'Available'
        }
    ],
    'psoriasis': [
        {
            'name': 'Dr. Desai',
            'specialty': 'Dermatologist',
            'hospital': 'Narayana Health',
            'city': 'Bangalore',
            'fees': 500,
            'duration': 30,
            'timing': 'Mon-Sat 10AM-6PM',
            'rating': 4.8,
            'experience': '17 years',
            'languages': ['English', 'Hindi', 'Kannada', 'Tamil'],
            'availability': 'Available'
        }
    ]
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
            
            # For now, use a generic analysis (in production, use Google Vision API)
            # Simple disease detection based on description
            disease_description = request.POST.get('description', '').strip()
            
            if not disease_description:
                return render(request, 'reports/disease_detector.html', {'error': 'Please describe your symptom'})
            
            # Save report
            report = MedicalReport(selected_language=lang)
            report.report_image = report_file
            report.extracted_text = disease_description
            report.save()
            
            lang_name = LANGUAGE_NAMES[lang]
            
            try:
                # AI Analysis
                response = client.chat.completions.create(
                    model='llama-3.3-70b-versatile',
                    messages=[
                        {
                            "role": "system",
                            "content": f"""You are MediSathi, a medical symptom analyzer. Respond ONLY in {lang_name}.
Analyze the symptom and provide:
1. Likely disease/condition
2. Risk level (GREEN/YELLOW/RED)
3. What it is (definition)
4. Why it happens (causes)
5. Home remedies (Indian)
6. Foods to eat
7. Foods to avoid
8. When to see doctor"""
                        },
                        {
                            "role": "user",
                            "content": f"""Patient's Symptom/Photo Description:
{disease_description}

Provide detailed analysis in {lang_name}:

🩺 LIKELY DISEASE/CONDITION:
[Name]

⚠️ RISK LEVEL:
[GREEN/YELLOW/RED]

📚 What is it?
[Short definition]

❓ Why does this happen?
[Causes]

🌿 HOME REMEDIES:
- Remedy 1: [benefit]
- Remedy 2: [benefit]
- Remedy 3: [benefit]

🍽️ FOODS TO EAT:
- Food 1: [benefit]
- Food 2: [benefit]

❌ FOODS TO AVOID:
- Food 1: [why]
- Food 2: [why]

🏥 WHEN TO SEE DOCTOR:
[Urgency timeline]

Respond ONLY in {lang_name}"""
                        }
                    ],
                    max_tokens=2000,
                    temperature=0.7
                )
                
                result = response.choices[0].message.content
                
                report.ai_explanation = result
                report.risk_category = get_risk_category(result)
                report.save()
                
                return render(request, 'reports/disease_result.html', {
                    'report': report,
                    'explanation': result.strip(),
                    'risk': report.risk_category,
                    'language': lang_name,
                    'symptom': disease_description,
                })
            
            except Exception as api_error:
                return render(request, 'reports/disease_detector.html', {'error': f'Error: {str(api_error)}'})
        
        except Exception as e:
            return render(request, 'reports/disease_detector.html', {'error': str(e)})
    
    return render(request, 'reports/disease_detector.html')

def find_doctors(request):
    """Find online doctors for detected disease"""
    disease = request.GET.get('disease', '').lower()
    
    # Get doctors for this disease
    doctors = ONLINE_DOCTORS.get(disease, ONLINE_DOCTORS.get('fungal infection', []))
    
    return render(request, 'reports/doctor_finder.html', {
        'doctors': doctors,
        'disease': disease,
        'doctor_count': len(doctors)
    })

def book_consultation(request):
    """Book doctor consultation"""
    if request.method == 'POST':
        doctor_name = request.POST.get('doctor_name')
        doctor_fees = request.POST.get('doctor_fees')
        disease = request.POST.get('disease')
        
        return render(request, 'reports/booking_confirmation.html', {
            'doctor_name': doctor_name,
            'doctor_fees': doctor_fees,
            'disease': disease,
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
                response = client.chat.completions.create(
                    model='llama-3.3-70b-versatile',
                    messages=[
                        {
                            "role": "system",
                            "content": f"You are MediSathi health assistant. Respond ONLY in {lang_name}."
                        },
                        {
                            "role": "user",
                            "content": f"""Patient symptoms: {symptom_text}

Provide in {lang_name}:
🩺 What problem?
⚠️ Risk (GREEN/YELLOW/RED)?
🌿 Home remedies?
🍽️ Foods to eat?
❌ Foods to avoid?
🏥 When doctor?"""
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