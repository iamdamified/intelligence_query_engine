# generate_test_csv.py
import csv
import random

GENDERS = ['male', 'female']
AGE_GROUPS = ['child', 'teenager', 'adult', 'senior']
COUNTRIES = [
    ('NG', 'Nigeria'), ('US', 'United States'), ('GH', 'Ghana'),
    ('GB', 'United Kingdom'), ('ZA', 'South Africa'), ('KE', 'Kenya'),
    ('IN', 'India'), ('CA', 'Canada'), ('AU', 'Australia'), ('DE', 'Germany'),
    ('FR', 'France'), ('BR', 'Brazil'), ('JP', 'Japan'), ('CN', 'China'),
    ('EG', 'Egypt'), ('ET', 'Ethiopia'), ('TZ', 'Tanzania'), ('UG', 'Uganda'),
    ('SN', 'Senegal'), ('CI', "Cote d'Ivoire"),
]

FIRST_NAMES = [
    'Amara','Bolu','Chidi','Dayo','Emeka','Funmi','Gbenga','Hauwa','Ifeoma',
    'Jide','Kemi','Lola','Musa','Ngozi','Ola','Pita','Qudus','Remi','Sola',
    'Tunde','Uche','Voke','Wale','Xola','Yemi','Zara','Adaeze','Babatunde',
    'Chiamaka','Dimma','Efosa','Folake','Godwin','Helen','Ikenna','Jumoke',
    'Kunle','Lawal','Mercy','Nkem','Obiora','Patience','Rasheed','Seun',
    'Toyin','Udoka','Victor','Wunmi','Ximena','Yvonne','Zainab','Ahmed',
    'Blessing','Cynthia','David','Esther','Felix','Grace','Henry','Irene',
    'James','Kehinde','Lydia','Moses','Nora','Onome','Precious','Queen',
    'Richard','Susan','Timothy','Usman','Vivian','William','Xerxes','Yusuf',
]

LAST_NAMES = [
    'Okonkwo','Adesanya','Mensah','Osei','Diallo','Traore','Kamara',
    'Ibrahim','Musa','Yusuf','Adekunle','Bakare','Chukwu','Dada',
    'Eze','Fashola','Ganiyu','Hassan','Idowu','Johnson','Kalu',
    'Lawal','Mba','Nwosu','Ogundele','Peters','Quadri','Raji',
    'Salami','Taiwo','Usman','Vincent','Williams','Xavier','Yakubu',
]

def get_age_group(age):
    if age <= 12: return 'child'
    if age <= 19: return 'teenager'
    if age <= 59: return 'adult'
    return 'senior'

rows = 10000  # Change to 500000 for a stress test
seen_names = set()

with open('test_profiles.csv', 'w', newline='', encoding='utf-8') as f:
    writer = csv.DictWriter(f, fieldnames=[
        'name','gender','gender_probability','age','age_group',
        'country_id','country_name','country_probability'
    ])
    writer.writeheader()

    written = 0
    attempts = 0

    while written < rows:
        attempts += 1
        first = random.choice(FIRST_NAMES)
        last = random.choice(LAST_NAMES)
        # Add number suffix to ensure uniqueness
        name = f"{first.lower()} {last.lower()} {attempts}"

        if name in seen_names:
            continue
        seen_names.add(name)

        gender = random.choice(GENDERS)
        age = random.randint(1, 85)
        country_code, country_name = random.choice(COUNTRIES)

        writer.writerow({
            'name': name,
            'gender': gender,
            'gender_probability': round(random.uniform(0.6, 0.99), 4),
            'age': age,
            'age_group': get_age_group(age),
            'country_id': country_code,
            'country_name': country_name,
            'country_probability': round(random.uniform(0.5, 0.95), 4),
        })
        written += 1

print(f"Done! Generated {written} rows in test_profiles.csv")