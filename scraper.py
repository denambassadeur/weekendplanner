import os
import requests
from bs4 import BeautifulSoup
import google.genai as genai
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
client = genai.Client(api_key=API_KEY)

# Belangrijk: Headers toevoegen zodat we niet geblokkeerd worden
HEADERS = {
    "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36"
}

BASE_URL = "https://www.lidl.be"
OFFERS_URL = "https://www.lidl.be/c/nl-BE/aanbiedingen/s10006730"

def get_links():
    print("Zoeken naar Lidl links...")
    try:
        r = requests.get(OFFERS_URL, headers=HEADERS, timeout=15)
        soup = BeautifulSoup(r.text, 'html.parser')
        links = {"week": None, "weekend": None}
        for a in soup.find_all('a', href=True):
            h = a['href']
            if "aanbiedingen-deze-week" in h and not links["week"]:
                links["week"] = BASE_URL + h if h.startswith('/') else h
            if "weekenddeals" in h and not links["weekend"]:
                links["weekend"] = BASE_URL + h if h.startswith('/') else h
        print(f"Links gevonden: {links}")
        return links
    except Exception as e:
        print(f"Link fout: {e}")
        return {}

def scrape_products(url):
    if not url: return ""
    print(f"Scrapen van: {url}")
    try:
        r = requests.get(url, headers=HEADERS, timeout=15)
        soup = BeautifulSoup(r.text, 'html.parser')
        
        # Lidl gebruikt vaak specifieke classes voor titels
        # We zoeken nu op meerdere mogelijke manieren
        items = []
        
        # Manier 1: Zoek op h2 en h3 (vaak gebruikt voor titels)
        for header in soup.find_all(['h2', 'h3']):
            text = header.get_text(strip=True)
            if len(text) > 5: # Filter korte ruis
                items.append(text)
        
        # Manier 2: Zoek op 'article' tags (kaarten)
        for article in soup.find_all('article'):
            text = article.get_text(strip=True)
            # Pak de eerste regel of een deel van de tekst
            first_line = text.split('\n')[0]
            if len(first_line) > 5:
                items.append(first_line)

        # Dubbelen verwijderen
        unique_items = list(set(items))
        print(f"Aantal producten gevonden op deze pagina: {len(unique_items)}")
        return "\n".join(unique_items)
    except Exception as e:
        print(f"Scrape fout: {e}")
        return ""

def ask_gemini(promo_data):
    print("Gemini aan het werk zetten...")
    try:
        response = client.models.generate_content(
            model="gemini-2.0-flash",
            contents=f"Hier zijn de promoties van deze week: {promo_data}. Maak op basis hiervan mijn weekendplan met recepten.",
            config=genai.types.GenerateContentConfig(
                system_instruction=SYSTEM_PROMPT
            )
        )
        return response.text
    except Exception as e:
        return f"Fout bij aanroepen Gemini: {e}"

if __name__ == "__main__":
    urls = get_links()
    
    data = ""
    data += scrape_products(urls.get("week"))
    data += "\n"
    data += scrape_products(urls.get("weekend"))
    
    # We sturen alleen data naar Gemini als we echt iets gevonden hebben
    if len(data.strip()) > 50: # Check of we genoeg tekst hebben
        inhoud = ask_gemini(data)
    else:
        print("WAARSCHUWING: Geen productdata gevonden!")
        inhoud = "Kon geen promoties ophalen. Waarschijnlijk blokkeert de website tijdelijk de toegang. Probeer het over een uur nog eens."

    nu = datetime.now().strftime("%d-%m-%Y %H:%M")
    html = f"""
    <html>
    <head><title>Weekend Planner</title></head>
    <body style="font-family:sans-serif; max-width:800px; margin:auto; padding:20px; line-height: 1.6;">
        <h1>Mijn Weekend Planner</h1>
        <div style="border:1px solid #ccc; padding:20px; border-radius:10px; background-color: #f9f9f9;">
            {inhoud}
        </div>
        <p><small>Update: {nu} (Belgische tijd)</small></p>
    </body>
    </html>
    """
    
    with open("index.html", "w", encoding="utf-8") as f:
        f.write(html)
    print("Klaar!")
