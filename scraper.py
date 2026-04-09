import os
import requests
from bs4 import BeautifulSoup
import google.genai as genai
from datetime import datetime
import re

# --- 1. CONFIGURATIE ---
MIJN_AGENDA = """
- Vrijdag: Werken tot 18u.
- Zaterdag: Padel (15u-17u).
- Zondag: Ouders komen lunchen (4 personen).
"""

INSTRUCTIES = f"""
Jij bent een culinaire assistent. 
GEBRUIK DEZE AGENDA: {MIJN_AGENDA}
TAAK:
1. Scan de lijst met woorden van de Lidl.
2. Als je echte producten herkent (vlees, vis, groenten), gebruik die voor je menu.
3. Als de lijst leeg is of alleen 'rommel' bevat, maak dan een 'Chef's Surprise' menu gebaseerd op typische Belgische seizoensproducten van april (zoals asperges of lentelam).
4. Antwoord in HTML.
"""

API_KEY = os.environ.get("GEMINI_API_KEY")
client = genai.Client(api_key=API_KEY)

HEADERS = {
    "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/123.0.0.0 Safari/537.36",
    "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,image/avif,image/webp,*/*;q=0.8",
    "Accept-Language": "nl-BE,nl;q=0.9,en-GB;q=0.8,en;q=0.7"
}

# --- 2. DE "ALLESVANGER" SCRAPER ---

def scrape_lidl_api(url):
    print("Op zoek naar de verborgen productlijst...")
    # We proberen de API-headers na te bootsen die de website gebruikt
    api_headers = {
        "User-Agent": "Mozilla/5.0",
        "Accept": "application/json",
        "x-requested-with": "XMLHttpRequest"
    }
    
    try:
        # We zoeken in de tekst naar de specifieke API-endpoint 
        # of we proberen de meest voorkomende datastructuur van Lidl
        r = requests.get(url, headers=HEADERS, timeout=15)
        
        # We zoeken naar een groot blok JSON-data dat vaak in de broncode staat
        # bij moderne websites (de 'Initial State')
        json_data = re.search(r'window\.__INITIAL_STATE__\s*=\s*({.*?});', r.text)
        
        if json_data:
            data = json.loads(json_data.group(1))
            # Hier moeten we diep graven in de mappen van de data
            # Dit is een voorbeeld, de exacte 'paden' kunnen variëren
            products = []
            # We zoeken recursief naar 'fullTitle' in de hele hoop data
            titles = re.findall(r'"fullTitle":"([^"]+)"', r.text)
            return list(set([t for t in titles if len(t) > 3]))
            
        return []
    except Exception as e:
        print(f"API Scrape fout: {e}")
        return []
def get_links():
    try:
        r = requests.get("https://www.lidl.be/c/nl-BE/aanbiedingen/s10006730", headers=HEADERS, timeout=15)
        soup = BeautifulSoup(r.text, 'html.parser')
        links = {"week": None, "weekend": None}
        for a in soup.find_all('a', href=True):
            h = a['href']
            if "aanbiedingen-deze-week" in h and not links["week"]:
                links["week"] = "https://www.lidl.be" + h if h.startswith('/') else h
            if "weekenddeals" in h and not links["weekend"]:
                links["weekend"] = "https://www.lidl.be" + h if h.startswith('/') else h
        return links
    except:
        return {"week": None, "weekend": None}

# --- 3. EXECUTIE ---

if __name__ == "__main__":
    urls = get_links()
    all_products = scrape_lidl_flexible(urls.get("week")) + scrape_lidl_flexible(urls.get("weekend"))
    
    print(f"--- DEBUG ---")
    print(f"Aantal items gevonden: {len(all_products)}")
    print(f"Eerste 5: {all_products[:5]}")
    
    # We roepen Gemini ALTIJD aan, ook als de lijst leeg is (voor de Chef's Surprise)
    prompt_data = "\n".join(all_products) if all_products else "GEEN DATA GEVONDEN (Gebruik seizoensproducten april)"
    
    response = client.models.generate_content(
        model="gemini-2.5-flash", 
        contents=f"Producten gevonden: {prompt_data}\n\nMaak mijn weekendplan.",
        config={'system_instruction': INSTRUCTIES}
    )
    
    nu = datetime.now().strftime("%d-%m-%Y %H:%M")
    with open("index.html", "w", encoding="utf-8") as f:
        f.write(f"""
        <html>
        <head>
            <title>Weekend Planner</title>
            <style>body{{font-family:sans-serif; max-width:800px; margin:auto; padding:30px; line-height:1.6; background:#f9f9f9;}} 
            .box{{background:#fff; padding:25px; border-radius:15px; box-shadow:0 5px 15px rgba(0,0,0,0.05);}}
            h1{{color:#0050aa;}}</style>
        </head>
        <body>
            <div class="box">
                <h1>🍴 Mijn Weekend Planner</h1>
                {response.text}
            </div>
            <p style='text-align:center; color:#999; font-size:0.8em;'>Laatste update: {nu}</p>
        </body>
        </html>
        """)
