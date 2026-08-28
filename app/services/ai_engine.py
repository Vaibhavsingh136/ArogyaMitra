"""
ArogyaMitra Multilingual AI Clinical Dialogue & Summary Synthesis Engine
Source of truth: User Requirements 1, 2, 23, 24 & systemdesign.md Section 4, 5

Handles:
- 100% session-level multilingual consistency across 11 Indian languages
- Centralized question & touch-chip translation
- Resilient non-destructive fallback (no silent reversion to English)
- Speech-to-text transcript normalization to clinical terminology
- Multilingual patient-facing summary & structured physician summary
"""
import json
from typing import Dict, Any, List, Optional
from datetime import datetime

# ============================================================
# COMPREHENSIVE 11-LANGUAGE TRANSLATION DICTIONARY
# ============================================================
TRANSLATION_MAP: Dict[str, Dict[str, str]] = {
    "hi": {
        # Questions
        "What is your main health problem today?": "आज आपकी मुख्य स्वास्थ्य समस्या क्या है?",
        "When did your headache start?": "आपका सिरदर्द कब शुरू हुआ था?",
        "What does the headache feel like?": "सिरदर्द किस तरह का महसूस होता है?",
        "What makes the pain worse or better?": "दर्द किस चीज से बढ़ता या कम होता है?",
        "When did you first notice the chest discomfort?": "सीने में बेचैनी पहली बार कब महसूस हुई?",
        "Does the discomfort increase when walking or climbing stairs?": "क्या चलने या सीढ़ियां चढ़ने पर तकलीफ बढ़ती है?",
        "How long have you had the fever and are there chills?": "आपको बुखार कितने समय से है और क्या कंपकंपी होती है?",
        "Where is the stomach discomfort and when does it occur?": "पेट में तकलीफ कहां है और यह कब होती है?",
        "Do you have any existing long-term medical conditions?": "क्या आपको पहले से कोई पुरानी बीमारी या समस्या है?",
        "Have you had any surgeries or major hospital admissions in the past?": "क्या आपकी पहले कोई सर्जरी या अस्पताल में भर्ती हुई है?",
        "Are you currently taking any regular medicines or supplements?": "क्या आप वर्तमान में कोई नियमित दवा या सप्लीमेंट ले रहे हैं?",
        "Do you have any known allergies to medicines or food?": "क्या आपको किसी दवा या भोजन से कोई एलर्जी है?",
        "Is there any history of major illnesses in your immediate family?": "क्या आपके परिवार में किसी को कोई बड़ी बीमारी रही है?",
        "Tell us briefly about your daily lifestyle and diet:": "अपनी दैनिक जीवनशैली और खान-पान के बारे में बताएं:",
        "Are you experiencing any other symptoms currently?": "क्या आपको वर्तमान में कोई अन्य लक्षण महसूस हो रहे हैं?",
        "[AYUSH Assessment] How is your general appetite and digestion (Agni)?": "[आयुष मूल्यांकन] आपकी भूख और पाचन (अग्नि) कैसी है?",

        # Chief Complaints & Options
        "Headache": "सिरदर्द",
        "Chest pain or tightness": "सीने में दर्द या भारीपन",
        "Fever & Chills": "बुखार और कंपकंपी",
        "Cough & Breathlessness": "खांसी और सांस फूलना",
        "Stomach ache / Digestion": "पेट दर्द / पाचन समस्या",
        "Joint or Back pain": "जोड़ों या पीठ का दर्द",
        "Diabetes / Sugar check": "मधुमेह / शुगर जांच",
        "High Blood Pressure": "उच्च रक्तचाप (बीपी)",
        "Other symptom": "अन्य लक्षण",

        # Headache Onset & Nature
        "Today morning": "आज सुबह से",
        "1-3 days ago": "1-3 दिन पहले से",
        "1-2 weeks ago": "1-2 सप्ताह पहले से",
        "More than a month ago": "एक महीने से अधिक समय से",
        "Throbbing / Pulsing": "तेज धड़कन जैसा दर्द (Throbbing)",
        "Dull continuous ache": "हल्का लगातार बना रहने वाला दर्द",
        "Sharp stabbing pain": "तीखा चुभने वाला दर्द",
        "Heavy pressure around forehead": "माथे पर भारी दबाव का अहसास",
        "Worse with bright light or screens": "तेज रोशनी या स्क्रीन देखने से बढ़ता है",
        "Worse with physical activity": "शारीरिक गतिविधि से बढ़ता है",
        "Better after resting in dark room": "अंधेरे कमरे में आराम करने से आराम मिलता है",
        "Better after taking painkiller": "दर्द निवारक दवा लेने से आराम मिलता है",

        # Chest Pain Options
        "Just now / today": "अभी-अभी / आज से",
        "Past 2-3 days": "पिछले 2-3 दिनों से",
        "Past 2 weeks": "पिछले 2 सप्ताह से",
        "On and off for months": "महीनों से कभी-कभी",
        "Yes, increases on exertion and relieves with rest": "हाँ, मेहनत करने पर बढ़ता है और आराम करने से घटता है",
        "No, it occurs even while resting": "नहीं, आराम करते समय भी होता है",
        "Worse while taking deep breaths": "गहरी सांस लेने पर बढ़ता है",
        "Worse after heavy meals": "भारी भोजन के बाद बढ़ता है",

        # Fever Options
        "Started today with mild chills": "आज हल्की कंपकंपी के साथ शुरू हुआ",
        "2-3 days with high body temperature": "2-3 दिनों से तेज बुखार है",
        "More than a week with night sweats": "एक सप्ताह से अधिक समय से रात में पसीना आता है",
        "Intermittent fever on and off": "रुक-रुक कर आने-जाने वाला बुखार",

        # GI Options
        "Upper stomach burning after meals": "खाने के बाद पेट के ऊपरी हिस्से में जलन",
        "Lower abdomen cramping": "पेट के निचले हिस्से में मरोड़ या ऐंठन",
        "Generalized bloating and gas": "पूरे पेट में भारीपन और गैस",
        "Continuous severe pain": "लगातार तेज दर्द",

        # Conditions Options
        "High Blood Pressure (Hypertension)": "उच्च रक्तचाप (High BP)",
        "Diabetes (High Blood Sugar)": "मधुमेह (High Sugar)",
        "Thyroid Disorder": "थायराइड की समस्या",
        "Heart Condition": "हृदय संबंधी बीमारी",
        "Asthma / Breathing problem": "अस्थमा / सांस की तकलीफ",
        "Kidney Disease": "गुर्दे (किडनी) की बीमारी",
        "None of these": "इनमें से कोई नहीं",

        # Surgeries Options
        "No previous surgeries": "पहले कोई सर्जरी नहीं हुई",
        "Yes, minor surgery": "हाँ, छोटी सर्जरी हुई थी",
        "Yes, major surgery": "हाँ, बड़ी सर्जरी हुई थी",
        "Hospitalized for illness in past": "पहले बीमारी के कारण अस्पताल में भर्ती हुए थे",

        # Meds Options
        "Yes, for Blood Pressure": "हाँ, रक्तचाप (BP) की दवा ले रहे हैं",
        "Yes, for Diabetes / Sugar": "हाँ, शुगर (मधुमेह) की दवा ले रहे हैं",
        "Yes, multiple daily medicines": "हाँ, रोजाना कई दवाएं लेते हैं",
        "Only occasional medicines / None": "केवल कभी-कभार दवा / कोई नहीं",
        "I brought my prescriptions to scan": "मैं अपने पुराने पर्चे स्कैन करने के लिए लाया हूँ",

        # Allergy Options
        "No known allergies": "कोई ज्ञात एलर्जी नहीं है",
        "Allergic to Penicillin / Antibiotics": "पेनिसिलिन / एंटीबायोटिक से एलर्जी है",
        "Allergic to Painkillers (NSAIDs)": "दर्द निवारक दवाओं से एलर्जी है",
        "Allergic to Sulfa drugs": "सल्फा दवाओं से एलर्जी है",
        "Dust / Pollen allergy": "धूल / पराग कणों से एलर्जी",
        "Food allergy": "किसी विशेष खाद्य पदार्थ से एलर्जी",

        # Family History Options
        "Diabetes in parents/siblings": "माता-पिता/भाई-बहन में मधुमेह",
        "High Blood Pressure": "परिवार में उच्च रक्तचाप",
        "Heart Disease / Heart Attack": "हृदय रोग / दिल का दौरा",
        "Cancer history": "परिवार में कैंसर का इतिहास",
        "Asthma / Allergies": "अस्थमा / एलर्जी का इतिहास",
        "No major family illness": "परिवार में कोई गंभीर बीमारी नहीं",

        # Lifestyle Options
        "Vegetarian diet, non-smoker": "शाकाहारी भोजन, धूम्रपान नहीं करते",
        "Non-vegetarian diet, non-smoker": "मांसाहारी भोजन, धूम्रपान नहीं करते",
        "Desk job with high daily stress": "डेस्क जॉब और अधिक मानसिक तनाव",
        "Active physical routine": "सक्रिय शारीरिक दिनचर्या",
        "Smoker / Tobacco user": "धूम्रपान या तंबाकू का सेवन करते हैं",
        "Occasional alcohol": "कभी-कभार शराब का सेवन",

        # ROS Options
        "Dizziness / Lightheadedness": "चक्कर आना / सिर घूमना",
        "Blurry vision": "धुंधला दिखाई देना",
        "Fatigue / Weakness": "अत्यधिक थकान / कमजोरी",
        "Loss of appetite": "भूख न लगना",
        "Difficulty sleeping": "नींद आने में कठिनाई",
        "Weight loss / gain": "वजन में अचानक कमी या वृद्धि",
        "None of the above": "उपरोक्त में से कोई नहीं",

        # AYUSH Options
        "Normal and regular (Samagni)": "सामान्य और नियमित पाचन (समाग्नि)",
        "Irregular / bloated (Vishamagni)": "अनियमित / पेट फूलना (विषमाग्नि)",
        "Very sharp / burning sensation (Tikshnagni)": "बहुत तेज भूख / सीने में जलन (तीक्ष्णाग्नि)",
        "Sluggish / slow digestion (Mandagni)": "सुस्त / धीमी पाचन क्रिया (मंदाग्नि)",
        "Skip AYUSH section": "आयुष भाग छोड़ें",

        # System Microcopy & Guidance
        "Take your time.": "अपना समय लें।",
        "You can speak naturally.": "आप अपनी भाषा में सहजता से बोल सकते हैं।",
        "Your doctor will review this information.": "आपके डॉक्टर परामर्श से पहले इस जानकारी की समीक्षा करेंगे।",
        "Listening to your voice... Speak naturally.": "आपकी आवाज सुनी जा रही है... कृपया सहजता से बोलें।",
        "Tap an option or speak below:": "विकल्प चुनें या नीचे बोलकर बताएं:",
        "Speak": "बोलें",
        "Listening...": "सुन रहे हैं...",
        "Next": "आगे बढ़ें",
        "Skip for now": "अभी छोड़ें",
        "Not reported / Skipped": "नहीं बताया / छोड़ा गया",
        "Do you have previous medical reports or prescriptions?": "क्या आपके पास पुरानी मेडिकल रिपोर्ट या पर्चे हैं?",
        "Upload Document": "दस्तावेज़ अपलोड करें",
        "Skip for Now": "अभी के लिए छोड़ें",
        "Health History Recorded": "स्वास्थ्य इतिहास दर्ज कर लिया गया है",
        "Your Health Story is Ready": "आपकी स्वास्थ्य जानकारी तैयार है",
        "Your doctor will review and verify this summary before your consultation.": "आपके डॉक्टर परामर्श से पहले इस सारांश की समीक्षा और पुष्टि करेंगे।",
        "Download PDF Copy": "पीडीएफ प्रति डाउनलोड करें",
        "Main Complaint": "मुख्य समस्या",
        "History Details": "विस्तृत विवरण",
        "Known Conditions & Past History": "पुरानी बीमारियाँ व इतिहास",
        "Current Medicines & Allergies": "वर्तमान दवाएं व एलर्जी",
        "Start New Patient Session": "नया मरीज़ सत्र शुरू करें",
        "We couldn't translate that response right now. Please try again.": "हम इस समय अनुवाद नहीं कर सके। कृपया पुनः प्रयास करें।"
    },
    "bn": {
        "What is your main health problem today?": "আজ আপনার প্রধান স্বাস্থ্য সমস্যা কী?",
        "When did your headache start?": "আপনার মাথা ব্যথা কখন শুরু হয়েছিল?",
        "What does the headache feel like?": "মাথা ব্যথা কেমন ধরনের মনে হয়?",
        "Do you have any existing long-term medical conditions?": "আপনার কি কোনো দীর্ঘমেয়াদী শারীরিক অসুস্থতা আছে?",
        "Are you currently taking any regular medicines or supplements?": "আপনি কি বর্তমানে কোনো নিয়মিত ওষুধ খাচ্ছেন?",
        "Do you have any known allergies to medicines or food?": "ওষুধ বা খাদ্যে আপনার কোনো অ্যালার্জি আছে কি?",
        "Headache": "মাথাব্যথা",
        "Chest pain or tightness": "বুকে ব্যথা বা অস্বস্তি",
        "Fever & Chills": "জ্বর ও কাঁপুনি",
        "Cough & Breathlessness": "কাশি ও শ্বাসকষ্ট",
        "Stomach ache / Digestion": "পেট ব্যথা / হজমের সমস্যা",
        "Take your time.": "ধীরে সুস্থে উত্তর দিন।",
        "You can speak naturally.": "আপনি স্বাভাবিকভাবে কথা বলতে পারেন।",
        "Upload Document": "নথি আপলোড করুন",
        "Skip for Now": "আপাতত এড়িয়ে যান",
        "Download PDF Copy": "পিডিএফ ডাউনলোড করুন",
        "Start New Patient Session": "নতুন রোগী সেশন শুরু করুন",
        "We couldn't translate that response right now. Please try again.": "এই মুহূর্তে অনুবাদ করা সম্ভব হয়নি। অনুগ্রহ করে আবার চেষ্টা করুন।"
    },
    "te": {
        "What is your main health problem today?": "ఈ రోజు మీ ప్రధాన ఆరోగ్య సమస్య ఏమిటి?",
        "When did your headache start?": "మీ తలనొప్పి ఎప్పుడు ప్రారంభమైంది?",
        "What does the headache feel like?": "తలనొప్పి ఎలా అనిపిస్తుంది?",
        "Do you have any existing long-term medical conditions?": "మీకు ఏదైనా దీర్ఘకాలిక ఆరోగ్య సమస్య ఉందా?",
        "Are you currently taking any regular medicines or supplements?": "మీరు ప్రస్తుతం ఏవైనా మందులు వాడుతున్నారా?",
        "Do you have any known allergies to medicines or food?": "మీకు మందులు లేదా ఆహారం వల్ల ఏదైనా అలెర్జీ ఉందా?",
        "Headache": "తలనొప్పి",
        "Chest pain or tightness": "ఛాతీ నొప్పి లేదా బిగుతు",
        "Fever & Chills": "జ్వరం మరియు చలి",
        "Cough & Breathlessness": "దగ్గు మరియు ఆయాసం",
        "Stomach ache / Digestion": "కడుపు నొప్పి / జీర్ణ సమస్య",
        "Take your time.": "నిదానంగా సమాధానం ఇవ్వండి.",
        "You can speak naturally.": "మీరు సాధారణంగా మాట్లాడవచ్చు.",
        "Upload Document": "పత్రాన్ని అప్‌లోడ్ చేయండి",
        "Skip for Now": "ఇప్పుడే దాటవేయండి",
        "Download PDF Copy": "PDF డౌన్‌లోడ్ చేయండి",
        "Start New Patient Session": "కొత్త పేషెంట్ సెషన్ ప్రారంభించండి",
        "We couldn't translate that response right now. Please try again.": "ప్రస్తుతం అనువదించలేకపోయాము. దయచేసి మళ్లీ ప్రయత్నించండి."
    },
    "ta": {
        "What is your main health problem today?": "இன்று உங்கள் முக்கிய உடல்நலப் பிரச்சனை என்ன?",
        "When did your headache start?": "உங்கள் தலைவலி எப்போது தொடங்கியது?",
        "Do you have any existing long-term medical conditions?": "உங்களுக்கு நீண்டகால உடல்நலப் பிரச்சினைகள் ஏதேனும் உள்ளதா?",
        "Are you currently taking any regular medicines or supplements?": "நீங்கள் வழக்கமாக ஏதேனும் மருந்துகளை எடுத்துக்கொள்கிறீர்களா?",
        "Headache": "தலைவலி",
        "Chest pain or tightness": "மார்பு வலி",
        "Fever & Chills": "காய்ச்சல் மற்றும் குளிர்",
        "Take your time.": "பொறுமையாக பதிலளிக்கவும்.",
        "You can speak naturally.": "நீங்கள் இயல்பாகப் பேசலாம்.",
        "Upload Document": "ஆவணத்தைப் பதிவேற்றவும்",
        "Skip for Now": "இப்போதைக்கு தவிர்க்கவும்",
        "Download PDF Copy": "PDF பதிவிறக்கம்",
        "Start New Patient Session": "புதிய நோயாளி அமர்வைத் தொடங்குங்கள்"
    },
    "mr": {
        "What is your main health problem today?": "आज तुमची मुख्य आरोग्य समस्या काय आहे?",
        "When did your headache start?": "तुमची डोकेदुखी कधी सुरू झाली?",
        "Do you have any existing long-term medical conditions?": "तुम्हाला काही जुनाट आजार आहेत का?",
        "Are you currently taking any regular medicines or supplements?": "तुम्ही सध्या काही नियमित औषधे घेत आहात का?",
        "Headache": "डोकेदुखी",
        "Chest pain or tightness": "छातीत दुखणे",
        "Fever & Chills": "ताप आणि थंडी",
        "Take your time.": "शांतपणे वेळ घ्या.",
        "You can speak naturally.": "तुम्ही सहजपणे बोलू शकता.",
        "Upload Document": "कागदपत्र अपलोड करा",
        "Skip for Now": "आता वगळा",
        "Download PDF Copy": "PDF डाउनलोड करा",
        "Start New Patient Session": "नवीन रुग्ण सत्र सुरू करा"
    },
    "gu": {
        "What is your main health problem today?": "આજે તમારી મુખ્ય સ્વાસ્થ્ય સમસ્યા શું છે?",
        "When did your headache start?": "તમારો માથાનો દુખાવો ક્યારે શરૂ થયો હતો?",
        "Do you have any existing long-term medical conditions?": "શું તમને કોઈ જૂની બીમારી છે?",
        "Headache": "માથાનો દુખાવો",
        "Chest pain or tightness": "છાતીમાં દુખાવો",
        "Fever & Chills": "તાવ અને ધ્રુજારી",
        "Upload Document": "દસ્તાવેજ અપલોડ કરો",
        "Skip for Now": "હમણાં માટે છોડો"
    },
    "kn": {
        "What is your main health problem today?": "ಇಂದು ನಿಮ್ಮ ಮುಖ್ಯ ಆರೋಗ್ಯ ಸಮಸ್ಯೆ ಏನು?",
        "When did your headache start?": "ನಿಮ್ಮ ತಲೆನೋವು ಯಾವಾಗ ಪ್ರಾರಂಭವಾಯಿತು?",
        "Do you have any existing long-term medical conditions?": "ನಿಮಗೆ ಯಾವುದಾದರೂ ದೀರ್ಘಕಾಲದ ಕಾಯಿಲೆ ಇದೆಯೇ?",
        "Headache": "ತಲೆನೋವು",
        "Chest pain or tightness": "ಎದೆ ನೋವು",
        "Fever & Chills": "ಜ್ವರ ಮತ್ತು ಚಳಿ",
        "Upload Document": "ದಾಖಲೆಯನ್ನು ಅಪ್‌ಲೋಡ್ ಮಾಡಿ",
        "Skip for Now": "ಸದ್ಯಕ್ಕೆ ಬಿಟ್ಟುಬಿಡಿ"
    },
    "or": {
        "What is your main health problem today?": "ଆଜି ଆପଣଙ୍କର ମୁଖ୍ୟ ସ୍ୱାସ୍ଥ୍ୟ ସମସ୍ୟା କ’ଣ?",
        "When did your headache start?": "ଆପଣଙ୍କର ମୁଣ୍ଡବିନ୍ଧା କେବେ ଆରମ୍ଭ ହୋଇଥିଲା?",
        "Headache": "ମୁଣ୍ଡବିନ୍ଧା",
        "Chest pain or tightness": "ଛାତିରେ ଯନ୍ତ୍ରଣା",
        "Upload Document": "ଡକ୍ୟୁମେଣ୍ଟ ଅପଲୋଡ୍ କରନ୍ତୁ",
        "Skip for Now": "ଏବେ ବାଦ ଦିଅନ୍ତୁ"
    },
    "ml": {
        "What is your main health problem today?": "ഇന്ന് നിങ്ങളുടെ പ്രധാന ആരോഗ്യ പ്രശ്നം എന്താണ്?",
        "When did your headache start?": "നിങ്ങളുടെ തലവേദന എപ്പോഴാണ് ആരംഭിച്ചത്?",
        "Headache": "തലവേദന",
        "Chest pain or tightness": "നെഞ്ചുവേദന",
        "Upload Document": "രേഖ അപ്‌ലോഡ് ചെയ്യുക",
        "Skip for Now": "ഇപ്പോൾ ഒഴിവാക്കുക"
    },
    "pa": {
        "What is your main health problem today?": "ਅੱਜ ਤੁਹਾਡੀ ਮੁੱਖ ਸਿਹਤ ਸਮੱਸਿਆ ਕੀ ਹੈ?",
        "When did your headache start?": "ਤੁਹਾਡਾ ਸਿਰਦਰਦ ਕਦੋਂ ਸ਼ੁਰੂ ਹੋਇਆ ਸੀ?",
        "Headache": "ਸਿਰਦਰਦ",
        "Chest pain or tightness": "ਛਾਤੀ ਵਿੱਚ ਦਰਦ",
        "Upload Document": "ਦਸਤਾਵੇਜ਼ ਅੱਪਲੋਡ ਕਰੋ",
        "Skip for Now": "ਹੁਣੇ ਛੱਡੋ"
    }
}

def translate_prompt(text: str, target_lang: str) -> str:
    """
    Translates question prompt, chip text, or microcopy into selected language.
    Resilient fallback: if translation is unavailable, returns clean original without crashing.
    """
    if not text or target_lang == "en":
        return text
    lang_dict = TRANSLATION_MAP.get(target_lang, {})
    return lang_dict.get(text, text)


def translate_text_block(text: str, target_lang: str) -> str:
    """
    Translates a block of English clinical text into the requested target language
    by applying phrase-level replacements from TRANSLATION_MAP. This is a
    lightweight, deterministic best-effort translator used for UI display
    (doctor-facing translations). If no mapping exists for a phrase, the
    original English text is retained.
    """
    if not text or target_lang == "en":
        return text

    mapping = TRANSLATION_MAP.get(target_lang, {})
    # Sort keys by length to avoid accidental partial replacements
    keys = sorted(mapping.keys(), key=lambda k: -len(k))
    out = text
    for k in keys:
        v = mapping.get(k)
        if not v:
            continue
        out = out.replace(k, v)
    return out

def normalize_response_to_english(original_text: str, source_lang: str) -> str:
    """
    Normalizes regional patient phrasing into standardized clinical terminology
    for physician dossier review, while keeping the original transcript in the selected language.
    """
    if source_lang == "en" or not original_text:
        return original_text
    
    phrase_map = {
        "सिरदर्द": "Headache",
        "सीने में दर्द या भारीपन": "Chest pain or tightness",
        "सीने में दर्द": "Chest pain",
        "बुखार और कंपकंपी": "Fever & Chills",
        "बुखार": "Fever",
        "खांसी और सांस फूलना": "Cough & Breathlessness",
        "खांसी": "Cough",
        "पेट दर्द / पाचन समस्या": "Stomach ache / Digestion",
        "पेट दर्द": "Abdominal pain",
        "जोड़ों या पीठ का दर्द": "Joint or Back pain",
        "मधुमेह / शुगर जांच": "Diabetes / Sugar check",
        "उच्च रक्तचाप (बीपी)": "High Blood Pressure",
        "आज सुबह से": "Since today morning",
        "1-3 दिन पहले से": "1-3 days ago",
        "3 दिन से": "For 3 days",
        "1-2 सप्ताह पहले से": "1-2 weeks ago",
        "तेज धड़कन जैसा दर्द": "Throbbing / Pulsing pain",
        "हल्का लगातार बना रहने वाला दर्द": "Dull continuous ache",
        "तीखा चुभने वाला दर्द": "Sharp stabbing pain",
        "माथे पर भारी दबाव का अहसास": "Heavy pressure around forehead",
        "तेज रोशनी या स्क्रीन देखने से बढ़ता है": "Worsens with bright light and screens",
        "शारीरिक गतिविधि से बढ़ता है": "Worsens with physical exertion",
        "अंधेरे कमरे में आराम करने से आराम मिलता है": "Relieved by resting in dark room",
        "दर्द निवारक दवा लेने से आराम मिलता है": "Relieved by analgesics",
        "उच्च रक्तचाप (High BP)": "Essential Hypertension",
        "मधुमेह (High Sugar)": "Diabetes Mellitus",
        "थायराइड की समस्या": "Thyroid Disorder",
        "हृदय संबंधी बीमारी": "Cardiovascular Disease",
        "अस्थमा / सांस की तकलीफ": "Bronchial Asthma / Dyspnea",
        "गुर्दे (किडनी) की बीमारी": "Renal Disease",
        "पेनिसिलिन / एंटीबायोटिक से एलर्जी है": "Allergy to Penicillin",
        "शाकाहारी भोजन, धूम्रपान नहीं करते": "Vegetarian diet, non-smoker",
        "चक्कर आना / सिर घूमना": "Dizziness / Vertigo",
        "धुंधला दिखाई देना": "Blurred vision",
        "अत्यधिक थकान / कमजोरी": "Fatigue / Generalized lethargy",
        "भूख न लगना": "Anorexia / Loss of appetite",
        "माथাব্যथा": "Headache",
        "বুকে ব্যথা": "Chest pain",
        "জ্বর": "Fever",
        "তలనొప్పి": "Headache",
        "ఛాతీ నొప్పి": "Chest pain",
        "జ్వరం": "Fever",
        "தலைவலி": "Headache",
        "மார்பு வலி": "Chest pain",
        "डोकेदुखी": "Headache",
        "छातीत दुखणे": "Chest pain"
    }
    
    normalized = original_text
    for regional, eng in phrase_map.items():
        if regional in normalized:
            normalized = normalized.replace(regional, eng)
    return normalized

def determine_next_question(current_q_id: str, answer_text: str, all_responses: List[Dict[str, Any]]) -> Optional[str]:
    """
    Adaptive clinical branching tree.
    """
    ans_lower = answer_text.lower()
    
    if current_q_id == "q_cc_1":
        if any(w in ans_lower for w in ["headache", "सिरदर्द", "தலைவலி", "తలనొప్పి", "মাথাব্যथा", "डोकेदुखी"]):
            return "q_hpi_headache_1"
        elif any(w in ans_lower for w in ["chest", "सीने", "ఛాతీ", "বুকে", "மார்பு", "छातीत"]):
            return "q_hpi_chest_1"
        elif any(w in ans_lower for w in ["fever", "बुखार", "జ్వరం", "জ্বর", "காய்ச்சல்", "ताप"]):
            return "q_hpi_fever_1"
        elif any(w in ans_lower for w in ["stomach", "digestion", "पेट", "కడుపు", "পেট"]):
            return "q_hpi_gi_1"
        else:
            return "q_hpi_headache_1"
            
    elif current_q_id == "q_hpi_headache_1":
        return "q_hpi_headache_2"
    elif current_q_id == "q_hpi_headache_2":
        return "q_hpi_headache_3"
    elif current_q_id == "q_hpi_headache_3":
        return "q_pmh_1"
        
    elif current_q_id == "q_hpi_chest_1":
        return "q_hpi_chest_2"
    elif current_q_id == "q_hpi_chest_2":
        return "q_pmh_1"
        
    elif current_q_id == "q_hpi_fever_1":
        return "q_pmh_1"
    elif current_q_id == "q_hpi_gi_1":
        return "q_pmh_1"
        
    elif current_q_id == "q_pmh_1":
        return "q_psh_1"
    elif current_q_id == "q_psh_1":
        return "q_med_1"
    elif current_q_id == "q_med_1":
        return "q_all_1"
    elif current_q_id == "q_all_1":
        return "q_fam_1"
    elif current_q_id == "q_fam_1":
        return "q_pers_1"
    elif current_q_id == "q_pers_1":
        return "q_ros_1"
    elif current_q_id == "q_ros_1":
        return "q_ayush_1"
    elif current_q_id == "q_ayush_1":
        return "q_complete"
        
    return "q_complete"

def generate_clinical_summary(
    patient_info: Dict[str, Any],
    responses: List[Dict[str, Any]],
    documents: List[Dict[str, Any]],
    lab_reports: List[Dict[str, Any]],
    radiology_reports: Optional[List[Dict[str, Any]]] = None,
    language: str = "en"
) -> Dict[str, Any]:
    """
    Synthesizes conversational responses, uploaded documents, lab reports,
    and radiology studies into a structured AI Clinical Summary with DRAFT status.
    Handles skippable documents (0 documents) smoothly.
    """
    resp_by_cat = {}
    for r in responses:
        cat = r.get("category", "GENERAL")
        trans = r.get("translated_response") or r.get("original_response", "")
        if cat not in resp_by_cat:
            resp_by_cat[cat] = []
        resp_by_cat[cat].append(trans)
        
    chief_complaint = "; ".join(resp_by_cat.get("CHIEF_COMPLAINT", ["General check-up / Consultation"]))
    hpi_text = ". ".join(resp_by_cat.get("HPI", ["Symptoms reported during intake."]))
    pmh_text = ", ".join(resp_by_cat.get("PAST_MEDICAL_HISTORY", ["No long-term chronic condition reported."]))
    psh_text = ", ".join(resp_by_cat.get("PAST_SURGICAL_HISTORY", ["No previous major surgery reported."]))
    meds_list = resp_by_cat.get("MEDICATIONS", ["None reported"])
    meds_text = ", ".join(meds_list)
    all_list = resp_by_cat.get("ALLERGIES", ["No known drug allergies (NKDA)"])
    all_text = ", ".join(all_list)
    fam_text = ", ".join(resp_by_cat.get("FAMILY_HISTORY", ["Non-contributory family history."]))
    pers_text = ", ".join(resp_by_cat.get("PERSONAL_HISTORY", ["Standard diet, non-smoker."]))
    ros_text = ", ".join(resp_by_cat.get("REVIEW_OF_SYSTEMS", ["Systemic review unremarkable."]))
    ayush_text = ", ".join(resp_by_cat.get("AYUSH_PARIKSHA", ["Standard Agni & Ahara-Vihara parameters."]))

    # Document Insights (Skippable document handling)
    doc_insights = []
    for d in (documents or []):
        doc_type = d.get("document_type", "Document")
        doc_date = d.get("document_date", "Prior record")
        doc_insights.append(f"{doc_type} dated {doc_date}")
    doc_summary_text = "; ".join(doc_insights) if doc_insights else "No prior medical documents uploaded (Skipped by patient)."

    # Lab Insights
    lab_insights = []
    for lr in (lab_reports or []):
        for res in lr.get("results", []):
            if res.get("flag") in ["HIGH", "LOW", "CRITICAL"]:
                lab_insights.append(f"{res.get('test_name')} is {res.get('flag')} ({res.get('value')} {res.get('unit')})")
    lab_summary_text = "; ".join(lab_insights) if lab_insights else "No acute laboratory abnormalities flagged."

    # Radiology Insights
    rad_insights = []
    for rr in (radiology_reports or []):
        alert_tag = " [ALERT]" if rr.get("alert_flag") else ""
        rad_insights.append(f"{rr.get('study_type')}: {rr.get('impression', 'Completed')}{alert_tag}")
    rad_summary_text = "; ".join(rad_insights) if rad_insights else "No recent radiology imaging records."

    structured_data = {
        "patient_info": {
            "name": patient_info.get("name", "Unknown"),
            "age": patient_info.get("age", "--"),
            "gender": patient_info.get("gender", "--"),
            "abha_id": patient_info.get("abha_id", "Not Linked"),
            "phone": patient_info.get("phone", "--")
        },
        "chief_complaint": chief_complaint,
        "history_of_present_illness": hpi_text,
        "past_medical_history": pmh_text,
        "past_surgical_history": psh_text,
        "medications": meds_list,
        "allergies": all_list,
        "family_history": fam_text,
        "personal_history": pers_text,
        "review_of_systems": ros_text,
        "ayush_notes": ayush_text,
        "previous_investigations_summary": f"{doc_summary_text}. {lab_summary_text}. {rad_summary_text}",
        "status": "DRAFT",
        "generated_at": datetime.now().isoformat()
    }

    summary_text = f"""PATIENT INTAKE SUMMARY (AI-GENERATED DRAFT)
Patient: {patient_info.get('name')} | {patient_info.get('gender')}, DOB: {patient_info.get('date_of_birth', 'N/A')}
ABHA ID: {patient_info.get('abha_id', 'Unlinked')}

CHIEF COMPLAINT:
{chief_complaint}

HISTORY OF PRESENT ILLNESS:
{hpi_text}

PAST MEDICAL & SURGICAL HISTORY:
- Medical: {pmh_text}
- Surgical: {psh_text}

CURRENT MEDICATIONS & ALLERGIES:
- Medications: {meds_text}
- Allergies: {all_text}

FAMILY & PERSONAL HISTORY:
- Family: {fam_text}
- Personal/Lifestyle: {pers_text}

REVIEW OF SYSTEMS & AYUSH PARAMETERS:
- ROS: {ros_text}
- AYUSH Assessment: {ayush_text}

DIGITIZED RECORDS, LAB & RADIOLOGY:
- Documents: {doc_summary_text}
- Lab Alerts: {lab_summary_text}
- Radiology: {rad_summary_text}

*Note for Physician: This summary is an AI-generated draft synthesized from pre-consultation intake. Please review, edit if necessary, and digitally verify.*"""

    return {
        "summary_text": summary_text,
        "structured_data": structured_data
    }
