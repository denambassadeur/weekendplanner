import os
import requests
from bs4 import BeautifulSoup
import google.genai as genai # Aangepaste import voor 2026
from datetime import datetime

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
API_KEY = os.environ.get("GEMINI_API_KEY")

# Initialiseer de client op de nieuwe 2026 manier
client = genai.Client(api_key=API_KEY)

BASE_URL = "https://www.lidl.be"
OFFERS_URL = "https://www.lidl.be/c/nl-BE/aanbiedingen/s10006730"

def get_links():
    print("Zoeken naar Lidl links...")
    try:
        r = requests.get(OFFERS_URL, timeout=10)
        soup = BeautifulSoup(r.text, 'html.parser')
        links = {"week": None, "weekend": None}
        for a in soup.find_all('a', href=True):
            h = a['href']
            if "aanbiedingen-deze-week" in h and not links["week"]:
                links["week"] = BASE_URL + h if h.startswith('/') else h
            if "weekenddeals" in h and not links["weekend"]:
                links["weekend"] = BASE_URL + h if h.startswith('/') else h
        return links
    except Exception as e:
        print(f"Link fout: {e}")
        return {}

def scrape_products(url):
    if not url: return ""
    print(f"Scrapen: {url}")
    try:
        r = requests.get(url, timeout=10)
        soup = BeautifulSoup(r.text, 'html.parser')
        # We halen alle koppen (h3) op, dat zijn meestal de producten
        items = [i.get_text(strip=True) for i in soup.find_all('h3')]
        return "\n".join(set(items))
    except:
        return ""

def ask_gemini(promo_data):
    print("Gemini aan het werk zetten...")
    # De nieuwe 2026 syntax voor de client
    response = client.models.generate_content(
        model="gemini-2.0-flash",
        contents=f"Promoties: {promo_data}. Maak mijn plan.",
        config=genai.types.GenerateContentConfig(
            system_instruction=SYSTEM_PROMPT
        )
    )
    return response.text

if __name__ == "__main__":
    # 1. Links halen
    urls = get_links()
    
    # 2. Producten verzamelen
    data = ""
    if urls.get("week"): data += scrape_products(urls["week"])
    if urls.get("weekend"): data += scrape_products(urls["weekend"])
    
    # 3. Plan maken
    if data:
        inhoud = ask_gemini(data)
    else:
        inhoud = "Kon geen promoties ophalen. Controleer de Lidl website."

    # 4. HTML maken
    nu = datetime.now().strftime("%d-%m-%Y %H:%M")
    html = f"""
    <html>
    <head><title>Weekend Planner</title></head>
    <body style="font-family:sans-serif; max-width:800px; margin:auto; padding:20px;">
        <h1>Mijn Weekend Planner</h1>
        <div style="border:1px solid #ccc; padding:20px; border-radius:10px;">
            {inhoud}
        </div>
        <p><small>Update: {nu}</small></p>
    </body>
    </html>
    """
    
    with open("index.html", "w", encoding="utf-8") as f:
        f.write(html)
    print("Klaar! index.html is bijgewerkt.")
