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

def scrape_lidl_flexible(url):
    if not url: return []
    print(f"Poging tot scrapen: {url}")
    found_items = []
    try:
        r = requests.get(url, headers=HEADERS, timeout=15)
        html = r.text
        soup = BeautifulSoup(html, 'html.parser')
        
        # Methode 1: Zoek naar tekst die tussen aanhalingstekens staat bij "fullTitle" of "name"
        # Dit haalt data uit de verborgen Javascript objecten
        matches = re.findall(r'"fullTitle":"([^"]+)"', html)
        found_items.extend(matches)
        
        # Methode 2: Zoek naar de bekende Lidl grid-titels
        for el in soup.select('h3, h2, .ret-o-card__headline'):
            text = el.get_text(strip=True)
            if 5 < len(text) < 40:
                found_items.append(text)

        # Opschonen van de lijst
        cleaned = list(set([i for i in found_items if len(i) > 3 and "Lidl" not in i]))
        return cleaned
    except Exception as e:
        print(f"Scrape fout: {e}")
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
        model="gemini-2.0-flash", 
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
