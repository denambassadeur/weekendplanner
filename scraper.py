import os
import requests
from bs4 import BeautifulSoup
from google import genai # Nieuwe bibliotheek voor 2026
import datetime

# --- CONFIGURATIE ---

# 1. Plak hier de tekst/instructies uit je 'Kookrecepten' Gem
SYSTEM_INSTRUCTION = """
Doel en Doelstellingen:

* Help gebruikers bij het ontdekken van unieke en cultureel rijke recepten van over de hele wereld.
* Focus op typische lokale gerechten, historische recepten, gerechten met een bijzonder verhaal en gerechten die bij speciale gelegenheden worden geserveerd.
* Deel de passie voor koken als een enthousiaste amateurkok die altijd op zoek is naar nieuwe smaken.

Regels en Gedrag:

1) Keuze van Gerechten:
 a) Geef bij elke interactie precies 3 suggesties voor gerechten.
 b) Zorg ervoor dat de suggesties passen binnen de thema's: lokaal, historisch, verhalend of feestelijk.
 c) Geef voor elk gerecht een korte beschrijving van de oorsprong, het bijbehorende verhaal of de gelegenheid waarbij het gegeten wordt.


2) Interactie:

 a) Stel jezelf voor als een nieuwsgierige amateurkok.
 b) Gebruik een informele, enthousiaste toon die passie voor eten uitstraalt.


3) Presentatie:
 a) Gebruik lijstjes voor de 3 suggesties om het overzichtelijk te houden.
 b) Eindig je antwoord altijd met een vraag om de gebruiker te betrekken bij het kookproces.

Algemene Toon:
* Toegankelijk, warm en gepassioneerd.
* Gebruik begrijpelijke taal zonder te veel technisch jargon.
* Focus op het verhaal achter het eten om de ervaring te verrijken.
"""

# 2. Gemini API Setup
API_KEY = os.getenv("GEMINI_API_KEY")
# Initialiseer de nieuwe client
client = genai.Client(api_key=API_KEY)

BASE_URL = "https://www.lidl.be"
OFFERS_HOME = "https://www.lidl.be/c/nl-BE/aanbiedingen/s10006730"

# --- FUNCTIES ---

def get_latest_promo_urls():
    print("Links zoeken op Lidl.be...")
    try:
        response = requests.get(OFFERS_HOME, timeout=10)
        soup = BeautifulSoup(response.text, 'html.parser')
        links = {"week": None, "weekend": None}
        for a in soup.find_all('a', href=True):
            href = a['href']
            if "aanbiedingen-deze-week" in href and not links["week"]:
                links["week"] = BASE_URL + href if href.startswith('/') else href
            if "weekenddeals" in href and not links["weekend"]:
                links["weekend"] = BASE_URL + href if href.startswith('/') else href
        return links
    except Exception as e:
        print(f"Fout bij ophalen links: {e}")
        return {"week": None, "weekend": None}

def scrape_lidl_products(url):
    if not url: return ""
    print(f"Producten scrapen van: {url}")
    try:
        response = requests.get(url, timeout=10)
        soup = BeautifulSoup(response.text, 'html.parser')
        products = [item.get_text(strip=True) for item in soup.find_all(['h3', 'article']) if len(item.get_text(strip=True)) > 3]
        return "\n".join(list(set(products)))
    except Exception as e:
        print(f"Fout bij scrapen: {e}")
        return ""

def generate_weekend_plan(promo_data):
    print("Gemini raadplegen via de nieuwe GenAI API...")
    
    prompt = f"Hier zijn de Lidl-promoties: {promo_data}. Maak een weekendplanning met recepten (HTML-formaat)."
    
    # Gebruik de nieuwe 2026 methode
    response = client.models.generate_content(
        model="gemini-3-flash-preview",
        contents=prompt,
        config={'system_instruction': SYSTEM_INSTRUCTION}
    )
    return response.text

# --- HOOFDPROCES ---

if __name__ == "__main__":
    promo_links = get_latest_promo_urls()
    all_promos = ""
    if promo_links["week"]:
        all_promos += "\n--- WEEKDEALS ---\n" + scrape_lidl_products(promo_links["week"])
    if promo_links["weekend"]:
        all_promos += "\n--- WEEKENDDEALS ---\n" + scrape_lidl_products(promo_links["weekend"])
    
    if all_promos.strip():
        final_html_body = generate_weekend_plan(all_promos)
    else:
        final_html_body = "<p>Geen promoties gevonden.</p>"

    timestamp = datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    
    full_html = f"""
    <!DOCTYPE html>
    <html lang="nl">
    <head><meta charset="UTF-8"><title>Weekend Planner</title></head>
    <body style="font-family: sans-serif; padding: 20px;">
        <div style="max-width: 800px; margin: auto; border: 1px solid #ddd; padding: 20px;">
            <h1>Mijn Weekend Planner</h1>
            {final_html_body}
            <hr>
            <p><small>Laatste update: {timestamp}</small></p>
        </div>
    </body>
    </html>
    """
    
    with open("index.html", "w", encoding="utf-8") as f:
        f.write(full_html)
    print("Klaar!")
