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

HEADERS = {
    "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36"
}

BASE_URL = "https://www.lidl.be"
OFFERS_URL = "https://www.lidl.be/c/nl-BE/aanbiedingen/s10006730"

# --- 2. FUNCTIES ---

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
        return links
    except Exception as e:
        print(f"Link fout: {e}")
        return {}

def scrape_products(url):
    if not url: return ""
    print(f"Scrapen van: {url}")
    items = []
    try:
        r = requests.get(url, headers=HEADERS, timeout=15)
        soup = BeautifulSoup(r.text, 'html.parser')
        for header in soup.find_all(['h2', 'h3']):
            text = header.get_text(strip=True)
            if len(text) > 4:
                items.append(text)
        return "\n".join(set(items))
    except:
        return ""

def ask_gemini(promo_data):
    print("Gemini aanroepen...")
    try:
        # Hier gebruiken we SYSTEM_PROMPT. Let op de hoofdletters!
        response = client.models.generate_content(
            model="gemini-2.0-flash",
            contents=f"Hier zijn de promoties: {promo_data}. Maak mijn plan.",
            config={
                'system_instruction': SYSTEM_PROMPT
            }
        )
        return response.text
    except Exception as e:
        return f"Gemini fout: {str(e)}"

# --- 3. EXECUTIE ---

if __name__ == "__main__":
    urls = get_links()
    
    week_data = scrape_products(urls.get("week"))
    weekend_data = scrape_products(urls.get("weekend"))
    totaal_data = week_data + "\n" + weekend_data
    
    # Debugging print
    print(f"Data gevonden? {'Ja' if totaal_data.strip() else 'Nee'}")

    if len(totaal_data.strip()) > 10:
        inhoud = ask_gemini(totaal_data)
    else:
        inhoud = "Lidl blokkeert momenteel de scraper. Probeer het over een uur nog eens."

    nu = datetime.now().strftime("%d-%m-%Y %H:%M")
    
    html_output = f"""
    <html>
    <head>
        <title>Weekend Planner</title>
        <style>
            body {{ font-family: sans-serif; max-width: 800px; margin: 40px auto; padding: 20px; line-height: 1.6; color: #333; background-color: #f4f7f6; }}
            .card {{ border: 1px solid #ddd; padding: 30px; border-radius: 12px; background-color: #fff; box-shadow: 0 4px 12px rgba(0,0,0,0.1); }}
            h1 {{ color: #0050aa; border-bottom: 2px solid #0050aa; padding-bottom: 10px; }}
            h2 {{ color: #d32f2f; margin-top: 25px; }}
            ul {{ padding-left: 20px; }}
            .footer {{ text-align: center; margin-top: 20px; font-size: 0.85em; color: #777; }}
        </style>
    </head>
    <body>
        <div class="card">
            <h1>🍴 Mijn Weekend Planner</h1>
            {inhoud}
        </div>
        <p class="footer">Laatste update: {nu} (Belgische tijd)</p>
    </body>
    </html>
    """
    
    with open("index.html", "w", encoding="utf-8") as f:
        f.write(html_output)
    print("Done!")
