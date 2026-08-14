from django.shortcuts import render, redirect
from django.http import JsonResponse
from .models import MedicalReport
from groq import Groq
import os
import json
import requests
from bs4 import BeautifulSoup
import urllib.parse

client = Groq(api_key=os.getenv('GROQ_API_KEY'))

LANGUAGE_NAMES = {
    'english': 'English',
    'hindi': 'Hindi',
    'marathi': 'Marathi',
    'bengali': 'Bengali',
    'tamil': 'Tamil',
    'telugu': 'Telugu'
}

# Disease to Specialty Mapping
SPECIALTY_MAP = {
    'headache': 'neurologist',
    'migraine': 'neurologist',
    'fever': 'general physician',
    'cough': 'chest specialist',
    'cold': 'general physician',
    'acne': 'dermatologist',
    'fungal infection': 'dermatologist',
    'skin rash': 'dermatologist',
    'eczema': 'dermatologist',
    'psoriasis': 'dermatologist',
    'urticaria': 'dermatologist',
    'wound': 'general physician',
    'burn': 'general surgeon',
    'stomachache': 'gastroenterologist',
    'diarrhea': 'gastroenterologist',
    'allergy': 'allergist',
    'asthma': 'pulmonologist',
    'eye problem': 'ophthalmologist',
    'toothache': 'dentist',
    'hair loss': 'dermatologist',
    'fatigue': 'general physician',
    'chest pain': 'cardiologist',
    'high blood pressure': 'cardiologist',
    'diabetes': 'endocrinologist',
    'joint pain': 'orthopedic',
    'back pain': 'spine specialist',
}

def get_risk_category(text):
    t = (text or '').lower()
    if any(w in t for w in ['critical', 'urgent', 'severe', 'emergency']): 
        return 'red'
    if any(w in t for w in ['consult', 'doctor', 'soon', 'concerning']): 
        return 'yellow'
    return 'green'

def extract_hospital_name(address):
    """Extract hospital/clinic name from address"""
    if not address:
        return 'Clinic/Hospital'
    parts = address.split(',')
    return parts[0].strip() if parts else 'Clinic/Hospital'

def fetch_from_justdial(specialty, location):
    """Fetch real doctors from JustDial"""
    try:
        # Create JustDial search URL
        search_query = f"{specialty} in {location}"
        encoded_query = urllib.parse.quote(search_query)
        
        url = f"https://www.justdial.com/search?q={encoded_query}"
        
        headers = {
            'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36'
        }
        
        response = requests.get(url, headers=headers, timeout=10)
        response.raise_for_status()
        
        # Parse HTML
        soup = BeautifulSoup(response.content, 'html.parser')
        doctors = []
        
        # Extract doctor listings
        listings = soup.find_all('div', class_='listing-box-desc')
        
        for listing in listings[:15]:  # Get top 15
            try:
                # Get name
                name_elem = listing.find('a', class_='listing-name-link')
                if not name_elem:
                    name_elem = listing.find('a')
                name = name_elem.text.strip() if name_elem else 'Doctor'
                
                # Get address
                address_elem = listing.find('span', class_='area')
                address = address_elem.text.strip() if address_elem else f"{location}"
                
                # Get phone
                phone_elem = listing.find('span', class_='phonenumber')
                phone = phone_elem.text.strip() if phone_elem else 'Call for details'
                
                # Get rating
                rating_elem = listing.find('span', class_='jyrated')
                rating = '4.5'
                if rating_elem:
                    rating_text = rating_elem.text.strip()
                    try:
                        rating = float(rating_text.split('/')[0].split()[0])
                    except:
                        rating = 4.5
                
                # Get JustDial link
                link_elem = listing.find('a')
                link = link_elem['href'] if link_elem and link_elem.get('href') else f"https://www.justdial.com/search?q={name}"
                if not link.startswith('http'):
                    link = f"https://www.justdial.com{link}"
                
                # Extract city from address
                city = location
                if ',' in address:
                    city = address.split(',')[-1].strip()
                
                doctor = {
                    'name': name,
                    'specialty': specialty.title(),
                    'hospital': extract_hospital_name(address),
                    'city': city,
                    'address': address,
                    'phone': phone,
                    'rating': rating,
                    'fees': '300-500',
                    'duration': '20-30',
                    'timing': 'Call for timing',
                    'experience': 'Verified on JustDial',
                    'languages': ['English', 'Hindi', 'Local'],
                    'availability': 'Available',
                    'justdial_link': link,
                    'booking_link': link
                }
                
                if name and name != 'Doctor':
                    doctors.append(doctor)
                
            except Exception as e:
                print(f"Error parsing doctor: {e}")
                continue
        
        # If no doctors found, return search link
        if not doctors:
            search_url = f"https://www.justdial.com/search?q={specialty}+in+{location}"
            doctors = [{
                'name': f'Search {specialty} on JustDial',
                'specialty': specialty.title(),
                'hospital': 'Multiple Options',
                'city': location,
                'address': f'Search all {specialty} doctors in {location}',
                'phone': 'See listing',
                'rating': 4.5,
                'fees': 'Varies',
                'duration': '20',
                'timing': 'Varies',
                'experience': 'Verified',
                'languages': ['English', 'Hindi', 'Local'],
                'availability': 'Available',
                'justdial_link': search_url,
                'booking_link': search_url,
                'is_search_result': True
            }]
        
        return doctors
        
    except Exception as e:
        print(f"Error fetching from JustDial: {e}")
        # Return fallback with JustDial search link
        search_url = f"https://www.justdial.com/search?q={specialty}+in+{location}"
        return [{
            'name': f'Search {specialty} on JustDial',
            'specialty': specialty.title(),
            'hospital': 'Multiple Options',
            'city': location,
            'address': f'Search all doctors in {location}',
            'phone': 'See listing',
            'rating': 4.5,
            'fees': 'Varies',
            'duration': '20',
            'timing': 'Varies',
            'experience': 'Verified',
            'languages': ['English', 'Hindi', 'Local'],
            'availability': 'Available',
            'justdial_link': search_url,
            'booking_link': search_url,
            'is_search_result': True
        }]

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
1. Likely disease/condition name
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
    """Find real doctors using JustDial"""
    disease = request.GET.get('disease', 'doctor').lower()
    location = request.GET.get('location', '').lower()
    
    # Map disease to specialty
    specialty = SPECIALTY_MAP.get(disease.lower(), 'doctor')
    
    # Get user location if not provided
    if not location or location == 'india':
        location = request.GET.get('city', 'Mumbai')
    
    # Fetch from JustDial
    doctors = fetch_from_justdial(specialty, location)
    
    return render(request, 'reports/doctor_finder.html', {
        'doctors': doctors,
        'disease': disease,
        'location': location,
        'doctor_count': len(doctors),
        'specialty': specialty
    })

def book_consultation(request):
    """Book doctor consultation"""
    if request.method == 'POST':
        doctor_name = request.POST.get('doctor_name')
        justdial_link = request.POST.get('justdial_link', '#')
        booking_link = request.POST.get('booking_link', 'https://www.justdial.com')
        disease = request.POST.get('disease', '')
        
        return render(request, 'reports/booking_confirmation.html', {
            'doctor_name': doctor_name,
            'disease': disease,
            'booking_link': booking_link,
            'justdial_link': justdial_link,
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