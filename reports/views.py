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
    if any(w in t for w in ['critical', 'urgent', 'severe', 'emergency', 'immediate']): 
        return 'red'
    if any(w in t for w in ['consult', 'doctor', 'soon', 'concerning']): 
        return 'yellow'
    return 'green'

def home(request):
    return render(request, 'reports/home.html')

def voice_assistant(request):
    """Voice Health Assistant"""
    if request.method == 'POST':
        try:
            symptom_text = request.POST.get('symptoms', '').strip()
            lang = request.POST.get('language', 'english').lower()
            
            if not symptom_text:
                return render(request, 'reports/voice.html', {'error': 'Please speak or enter your symptoms'})
            
            if lang not in LANGUAGE_NAMES:
                lang = 'english'
            
            lang_name = LANGUAGE_NAMES[lang]
            
            # Save symptom record
            report = MedicalReport(selected_language=lang)
            report.extracted_text = symptom_text
            report.save()
            
            try:
                # Send to Groq for comprehensive health analysis
                response = client.chat.completions.create(
                    model='llama-3.3-70b-versatile',
                    messages=[
                        {
                            "role": "system",
                            "content": f"""You are MediSathi, a health assistant for Indian people. Respond ONLY in {lang_name}.
                            
You listen to health concerns and provide:
1. What the problem might be (possible conditions)
2. Why it happens (causes and reasons)
3. How serious it is (risk level)
4. What to do immediately (first aid)
5. When to see a doctor (urgency)
6. Home remedies specific to India
7. Diet recommendations (Indian food)
8. Foods to avoid
9. Lifestyle changes
10. Facts and explanations from medical knowledge
11. Relevant health tips

Be empathetic, detailed, practical, and safe."""
                        },
                        {
                            "role": "user",
                            "content": f"""Patient's Health Concern (in their own words):
{symptom_text}

Please provide comprehensive health guidance in {lang_name}:

📋 WHAT IS HAPPENING?
[List possible conditions/problems they might have]

❓ WHY DOES THIS HAPPEN?
[Explain causes and reasons for these symptoms]

⚠️ HOW SERIOUS IS IT?
[Assess risk level: GREEN (minor) / YELLOW (moderate) / RED (urgent)]
[Explain when to see doctor immediately]

🚨 WHAT TO DO RIGHT NOW?
[Immediate first aid or steps]

⏰ WHEN TO VISIT DOCTOR?
[Timeline and urgency]

🏥 WHAT SHOULD YOU TELL THE DOCTOR?
[Important details to mention]

🌿 HOME REMEDIES:
[Traditional Indian remedies that help]
[How to use them]
[How long they take]

🍽️ FOOD RECOMMENDATIONS:
[Indian foods that help your condition]
[Why they help]
[How to eat them]

❌ FOODS TO AVOID:
[Foods that make it worse]
[Why to avoid them]

💪 LIFESTYLE CHANGES:
[Daily habits to improve]
[Things to avoid]
[Rest and activity levels]

📚 IMPORTANT FACTS:
[Medical facts about this condition]
[How common it is]
[Risk factors]

✅ PREVENTION:
[How to prevent this in future]

---

OVERALL RISK LEVEL: [GREEN/YELLOW/RED]

SUMMARY:
[Brief summary of their situation]

DISCLAIMER:
This is general health information. Please consult a qualified doctor for proper diagnosis and treatment.

Respond ONLY in {lang_name}"""
                        }
                    ],
                    max_tokens=4000,
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

def upload_report(request):
    """Keep original medical report upload for reference"""
    if request.method == 'POST':
        return render(request, 'reports/upload.html', {'error': 'Please use Voice Assistant instead'})
    return render(request, 'reports/upload.html')

def history(request):
    try:
        reports = MedicalReport.objects.all().order_by('-created_at')[:10]
        return render(request, 'reports/history.html', {'reports': reports})
    except:
        return render(request, 'reports/history.html', {'reports': []})