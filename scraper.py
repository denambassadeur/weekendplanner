import os
import requests
from bs4 import BeautifulSoup
import google.genai as genai
from datetime import datetime

# --- 1. CONFIGURATIE ---
# We gebruiken hier een heel specifieke naam om verwarring te voorkomen
MIJN_CHEF_INSTRUCTIES = """
Jij bent mijn persoonlijke culinaire assistent. 
Focus op: groenten, fruit, vlees, vis en zuivel.
Maak een aantrekkelijk weekendmenu (lunch en diner) op basis van de Lidl-promoties.
Help gebruikers bij het ontdekken van unieke en cultureel rijke recepten van over de hele wereld.
Focus op typische lokale gerechten, historische recepten, gerechten met een bijzonder verhaal en gerechten die bij speciale gelegenheden worden geserveerd.
Zorg ervoor dat de suggesties passen binnen de thema's: lokaal, historisch, verhalend of feestelijk.
Geef voor elk gerecht een korte beschrijving van de oorsprong, het bijbehorende verhaal of de gelegenheid waarbij het gegeten wordt.
Presenteer het resultaat in nette HTML met titels (<h2>) en lijstjes (<ul>).
"""

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
        # We voegen een kleine pauze toe om minder op een robot te lijken
        import time
        time.sleep(2) 
        
        r = requests.get(url, headers=HEADERS, timeout=15)
        soup = BeautifulSoup(r.text, 'html.parser')
        
        # We zoeken nu heel breed in alle headers en sterke teksten
        # Dit zijn meestal de plaatsen waar productnamen staan
        for element in soup.find_all(['h2', 'h3', 'strong', 'span']):
            text = element.get_text(strip=True)
            
            # Filter: alleen tekst tussen de 5 en 60 tekens (echte productnamen)
            # En we sluiten woorden uit die zeker geen producten zijn
            verboden_woorden = ["lidl", "menu", "zoek", "aanmelden", "filiaal", "folder", "service", "cookies", "privacy"]
            
            if 5 < len(text) < 60:
                if not any(word in text.lower() for word in verboden_woorden):
                    items.append(text)
        
        # Dubbelen verwijderen
        unique_items = list(set(items))
        print(f"Items gevonden na filtering: {len(unique_items)}")
        
        # Voor de zekerheid: print de eerste 3 gevonden items in de logs
        if unique_items:
            print(f"Voorbeeld items: {unique_items[:3]}")
            
        return "\n".join(unique_items)
    except Exception as e:
        print(f"Scrape fout: {e}")
        return ""

def ask_gemini(promo_data):
    print("Gemini aanroepen...")
    prompt_opdracht = f"""
    Hieronder volgt een ruwe lijst van producten uit de Lidl-folder van deze week:
    ---
    {promo_data}
    ---
    GEBRUIK DEZE DATA:
    1. Kies minstens 5 specifieke producten uit de lijst hierboven.
    2. Verzin hiermee een creatief weekendmenu (lunch + diner).
    3. Als de lijst kort is, vul dan aan met basisproducten (olie, kruiden, rijst, pasta, aardappelen), maar vermeld de promo-items duidelijk.
    4. Antwoord direct in HTML-formaat.
    """
    
    # ... rest van je bestaande ask_gemini code met de fallback ...
    try:
        # Hier gebruiken we EXACT dezelfde naam: MIJN_CHEF_INSTRUCTIES
        response = client.models.generate_content(
            model="gemini-2.5-flash",
            contents=f"Hier zijn de promoties: {promo_data}. Maak mijn plan.",
            config={
                'system_instruction': MIJN_CHEF_INSTRUCTIES
            }
        )
        return response.text
    except Exception as e:
        # Dit vangt fouten op en laat ze zien op je website
        return f"Fout in ask_gemini functie: {str(e)}"

# --- 3. UITVOERING ---

if __name__ == "__main__":
    urls = get_links()
    
    # Producten ophalen
    data_week = scrape_products(urls.get("week"))
    data_weekend = scrape_products(urls.get("weekend"))
    totaal_tekst = data_week + "\n" + data_weekend
    
    print(f"Klaar met scrapen. Lengte data: {len(totaal_tekst)}")

    if len(totaal_tekst.strip()) > 10:
        inhoud_voor_site = ask_gemini(totaal_tekst)
    else:
        inhoud_voor_site = "Kon helaas geen promoties vinden op de Lidl website. Probeer het later nog eens."

    nu = datetime.now().strftime("%d-%m-%Y %H:%M")
    
    # De uiteindelijke HTML pagina
    html_template = f"""
    <html>
    <head>
        <title>Weekend Planner</title>
        <style>
            body {{ font-family: sans-serif; max-width: 800px; margin: 40px auto; padding: 20px; line-height: 1.6; background-color: #f8f9fa; }}
            .container {{ border: 1px solid #ddd; padding: 30px; border-radius: 12px; background-color: #fff; box-shadow: 0 4px 8px rgba(0,0,0,0.05); }}
            h1 {{ color: #0050aa; text-align: center; border-bottom: 2px solid #0050aa; padding-bottom: 10px; }}
            h2 {{ color: #d32f2f; }}
            .timestamp {{ text-align: center; font-size: 0.8em; color: #999; margin-top: 20px; }}
        </style>
    </head>
    <body>
        <div class="container">
            <h1>🍴 Mijn Weekend Planner</h1>
            <div id="content">
                {inhoud_voor_site}
            </div>
        </div>
        <p class="timestamp">Laatste update: {nu} (Belgische tijd)</p>
    </body>
    </html>
    """
    
    with open("index.html", "w", encoding="utf-8") as f:
        f.write(html_template)
    print("Succesvol afgerond!")
