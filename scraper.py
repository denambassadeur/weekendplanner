import os
import requests
from bs4 import BeautifulSoup
import google.generativeai as genai

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
GEMINI_API_KEY = os.getenv("GEMINI_API_KEY")
if not GEMINI_API_KEY:
    print("FOUT: Geen GEMINI_API_KEY gevonden in de environment variables.")
    exit(1)

genai.configure(api_key=GEMINI_API_KEY)
model = genai.GenerativeModel(
    model_name='gemini-1.5-flash',
    system_instruction=SYSTEM_INSTRUCTION
)

BASE_URL = "https://www.lidl.be"
OFFERS_HOME = "https://www.lidl.be/c/nl-BE/aanbiedingen/s10006730"

# --- FUNCTIES ---

def get_latest_promo_urls():
    """Zoekt de actuele links voor week- en weekenddeals op de Lidl website."""
    print("Links zoeken op Lidl.be...")
    try:
        response = requests.get(OFFERS_HOME, timeout=10)
        soup = BeautifulSoup(response.text, 'html.parser')
        
        links = {"week": None, "weekend": None}
        for a in soup.find_all('a', href=True):
            href = a['href']
            # Zoek naar de specifieke url-patronen
            if "aanbiedingen-deze-week" in href and not links["week"]:
                links["week"] = BASE_URL + href if href.startswith('/') else href
            if "weekenddeals" in href and not links["weekend"]:
                links["weekend"] = BASE_URL + href if href.startswith('/') else href
        return links
    except Exception as e:
        print(f"Fout bij ophalen links: {e}")
        return {"week": None, "weekend": None}

def scrape_lidl_products(url):
    """Haalt productnamen op van een specifieke promotiepagina."""
    if not url:
        return ""
    print(f"Producten scrapen van: {url}")
    try:
        response = requests.get(url, timeout=10)
        soup = BeautifulSoup(response.text, 'html.parser')
        
        # Lidl gebruikt vaak 'article' of specifieke classes voor hun productgrids
        products = []
        for item in soup.find_all(['h3', 'article']):
            text = item.get_text(strip=True)
            if len(text) > 3: # Filter korte ruis uit
                products.append(text)
        
        return "\n".join(list(set(products))) # Gebruik set() om dubbelen te voorkomen
    except Exception as e:
        print(f"Fout bij scrapen van {url}: {e}")
        return ""

def get_placeholder_calendar():
    """Placeholder voor je agenda. Later te vervangen door Google Calendar API."""
    return """
    - Vrijdagavond: Geen plannen, tijd om uitgebreid te koken.
    - Zaterdagmiddag: Sporten (14u - 16u).
    - Zondag: Familielunch, dus enkel een licht diner nodig.
    """

def generate_weekend_plan(promo_data, calendar_data):
    """Laat Gemini het plan maken."""
    print("Gemini raadplegen voor het weekendplan...")
    
    prompt = f"""
    Hier zijn de actuele Lidl-promoties:
    {promo_data}

    Dit is mijn agenda voor komend weekend:
    {calendar_data}

    STAPPENPLAN:
    1. Filter de promoties op: groenten, fruit, vlees, vis en zuivel.
    2. Maak een planning voor ontbijt, lunch en diner (vrijdagavond t.e.m. zondag).
    3. Zorg dat de gerechten passen bij de tijd die ik heb volgens mijn agenda.
    4. Geef de recepten en een compact boodschappenlijstje.
    
    OUTPUT: Schrijf alles in nette HTML-structuur (gebruik <h2>, <h3>, <ul> en <li>). 
    Geen <html> of <body> tags, enkel de inhoud.
    """
    
    response = model.generate_content(prompt)
    return response.text

# --- HOOFDPROCES ---

if __name__ == "__main__":
    # 1. Haal de links op
    promo_links = get_latest_promo_urls()
    
    # 2. Scrape de producten
    all_promos = ""
    if promo_links["week"]:
        all_promos += "\n--- WEEKDEALS ---\n" + scrape_lidl_products(promo_links["week"])
    if promo_links["weekend"]:
        all_promos += "\n--- WEEKENDDEALS ---\n" + scrape_lidl_products(promo_links["weekend"])
    
    # 3. Kalender ophalen
    my_calendar = get_placeholder_calendar()
    
    # 4. Planning genereren via Gemini
    if all_promos.strip():
        final_html_body = generate_weekend_plan(all_promos, my_calendar)
    else:
        final_html_body = "<p>Kon geen promoties vinden deze week. Probeer het later opnieuw.</p>"

    # 5. Opslaan als index.html
    full_html = f"""
    <!DOCTYPE html>
    <html lang="nl">
    <head>
        <meta charset="UTF-8">
        <meta name="viewport" content="width=device-width, initial-scale=1.0">
        <title>Weekend Planner - {os.getenv('GITHUB_REPOSITORY', 'Den Ambassadeur')}</title>
        <style>
            body {{ font-family: sans-serif; line-height: 1.6; padding: 20px; max-width: 800px; margin: auto; background-color: #f4f4f4; }}
            .container {{ background: white; padding: 30px; border-radius: 8px; box-shadow: 0 2px 10px rgba(0,0,0,0.1); }}
            h1 {{ color: #0050aa; border-bottom: 2px solid #0050aa; }}
            h2 {{ color: #333; margin-top: 30px; }}
            ul {{ padding-left: 20px; }}
            li {{ margin-bottom: 5px; }}
        </style>
    </head>
    <body>
        <div class="container">
            <h1>Mijn Weekend Planner</h1>
            {final_html_body}
            <hr>
            <p><small>Laatste update: {requests.utils.quote(str(requests.utils.datetime.datetime.now()))[:19]}</small></p>
        </div>
    </body>
    </html>
    """
    
    with open("index.html", "w", encoding="utf-8") as f:
        f.write(full_html)
    
    print("Succes! index.html is gegenereerd.")
