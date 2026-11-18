import os
import psycopg2
from dotenv import load_dotenv

load_dotenv()


def connect():
    return psycopg2.connect(
        host=os.getenv("DB_HOST", "localhost"),
        database=os.getenv("DB_NAME", "mediguide_db"),
        user=os.getenv("DB_USER", "postgres"),
        password=os.getenv("DB_PASSWORD", ""),
        port=os.getenv("DB_PORT", "5432"),
    )


DISEASES = [
    ("Diabetes", "Endocrine", "A condition involving high blood glucose levels.", "Increased thirst, frequent urination and tiredness.", "Insufficient insulin production or reduced insulin effectiveness.", "Healthy habits and regular health checks may reduce some risk factors.", "Medical assessment and glucose monitoring are important."),
    ("Asthma", "Respiratory", "A long-term condition affecting the airways.", "Wheezing, coughing, chest tightness and breathlessness.", "Airway inflammation and sensitivity to triggers.", "Identify triggers and follow a clinician-approved plan.", "Seek medical assessment. Severe breathing difficulty is an emergency."),
    ("Hypertension", "Cardiovascular", "Persistently high blood pressure.", "Often has no noticeable symptoms.", "Multiple genetic, lifestyle and health-related factors.", "Healthy eating, appropriate activity and regular blood pressure checks.", "A healthcare professional should assess and guide management."),
    ("Migraine", "Neurological", "A neurological condition involving recurring headache episodes.", "Headache, nausea and sensitivity to light or sound.", "Multiple neurological and environmental factors.", "Identify individual triggers and maintain regular sleep.", "Consult a healthcare professional for recurring headaches."),
    ("Anaemia", "Blood", "A condition involving low haemoglobin or healthy red blood cells.", "Fatigue, weakness, dizziness and breathlessness.", "Iron deficiency, vitamin deficiency, blood loss and other causes.", "Balanced nutrition and appropriate health checks.", "Testing is important to identify the underlying cause."),
    ("Pneumonia", "Respiratory", "An infection that inflames the air sacs in the lungs.", "Cough, fever, chest discomfort and breathing difficulty.", "Bacteria, viruses or fungi.", "Recommended vaccination and good hygiene.", "Medical assessment is important, especially with breathing difficulty."),
    ("Tuberculosis", "Infectious", "An infectious disease caused by tuberculosis bacteria.", "Persistent cough, fever, night sweats and weight loss.", "Spread through the air from someone with infectious TB.", "Early testing, diagnosis and appropriate treatment.", "Testing and a complete supervised treatment course are essential."),
    ("Dengue", "Infectious", "A viral infection transmitted by infected mosquitoes.", "Fever, headache, body pain, nausea and rash.", "Infection with dengue virus through mosquito bites.", "Prevent mosquito bites and remove standing water.", "Seek medical evaluation. Warning signs need urgent medical care."),
    ("Common Cold", "Infectious", "A viral infection affecting the upper respiratory tract.", "Runny nose, sneezing, cough and sore throat.", "Different respiratory viruses.", "Handwashing and avoiding close contact when ill.", "Rest and fluids may help. Seek advice for severe or persistent symptoms."),
    ("Influenza", "Infectious", "A contagious viral respiratory illness also called flu.", "Fever, cough, sore throat and body aches.", "Influenza viruses.", "Seasonal vaccination and good hygiene.", "High-risk individuals should seek timely medical advice."),
    ("Arthritis", "Musculoskeletal", "A group of conditions affecting the joints.", "Joint pain, swelling and stiffness.", "Causes vary by arthritis type.", "Appropriate physical activity and joint care.", "Professional assessment helps identify the type."),
    ("Hypothyroidism", "Endocrine", "A condition where the thyroid produces insufficient hormones.", "Tiredness, feeling cold and constipation.", "Autoimmune disease and other thyroid-related causes.", "Appropriate health assessment when symptoms or risk factors are present.", "Thyroid blood tests and professional guidance are important."),
    ("GERD", "Digestive", "A digestive condition involving repeated acid reflux.", "Heartburn and regurgitation.", "Reflux of stomach contents into the food pipe.", "Identify individual lifestyle and food triggers.", "Consult a healthcare professional for frequent symptoms."),
    ("Eczema", "Skin", "A group of conditions causing dry, irritated and itchy skin.", "Dryness, itching and inflammation.", "Genetic and environmental factors.", "Avoid known irritants and use suitable skin care.", "A healthcare professional can guide appropriate care."),
    ("Depression", "Mental Health", "A mental health condition affecting mood and daily life.", "Persistent low mood, loss of interest and sleep changes.", "Biological, psychological and social factors.", "Early support and access to mental healthcare.", "Consult a qualified mental health professional."),
]

FAQS = [
    ("What is a disease?", "A disease is a condition that affects the normal functioning of the body or mind.", "General Health"),
    ("What is a symptom?", "A symptom is a change or problem experienced by a person that may indicate a health condition.", "General Health"),
    ("Can MediGuide diagnose diseases?", "No. MediGuide provides educational information only and cannot diagnose medical conditions.", "Medical Safety"),
    ("How can I prevent infections?", "Hand hygiene, appropriate vaccination and recommended preventive measures can reduce infection risks.", "Prevention"),
    ("When should I consult a doctor?", "Seek professional advice for severe, persistent or worsening symptoms.", "Medical Safety"),
    ("Can I take medicines suggested by AI?", "Do not use AI-generated information as a prescription. Consult a qualified healthcare professional before taking medicines.", "Medical Safety"),
    ("What is blood pressure?", "Blood pressure is the force of blood pushing against the walls of blood vessels.", "General Health"),
    ("What is a healthy lifestyle?", "A healthy lifestyle includes balanced nutrition, suitable physical activity, adequate sleep and avoiding tobacco.", "Prevention"),
]


def main():
    with connect() as conn:
        with conn.cursor() as cur:
            cur.execute("""
                CREATE TABLE IF NOT EXISTS diseases (
                    id SERIAL PRIMARY KEY,
                    name VARCHAR(150) UNIQUE NOT NULL,
                    category VARCHAR(100),
                    description TEXT,
                    symptoms TEXT,
                    causes TEXT,
                    prevention TEXT,
                    care TEXT,
                    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
                )
            """)

            # Compatibility columns support older MediGuide database versions.
            cur.execute("ALTER TABLE diseases ADD COLUMN IF NOT EXISTS description TEXT")
            cur.execute("ALTER TABLE diseases ADD COLUMN IF NOT EXISTS care TEXT")
            cur.execute("ALTER TABLE diseases ADD COLUMN IF NOT EXISTS introduction TEXT")
            cur.execute("ALTER TABLE diseases ADD COLUMN IF NOT EXISTS general_care TEXT")

            cur.execute("""
                UPDATE diseases
                SET description = COALESCE(description, introduction),
                    care = COALESCE(care, general_care)
                WHERE description IS NULL OR care IS NULL
            """)

            cur.execute("""
                CREATE TABLE IF NOT EXISTS faq (
                    id SERIAL PRIMARY KEY,
                    question TEXT UNIQUE NOT NULL,
                    answer TEXT NOT NULL,
                    category VARCHAR(100),
                    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
                )
            """)

            for row in DISEASES:
                cur.execute("""
                    INSERT INTO diseases
                    (name, category, description, symptoms, causes, prevention, care)
                    VALUES (%s,%s,%s,%s,%s,%s,%s)
                    ON CONFLICT (name) DO NOTHING
                """, row)

            for row in FAQS:
                cur.execute("""
                    INSERT INTO faq (question, answer, category)
                    VALUES (%s,%s,%s)
                    ON CONFLICT (question) DO NOTHING
                """, row)

    print("MediGuide database initialized. Sample diseases and FAQs are ready.")


if __name__ == "__main__":
    main()