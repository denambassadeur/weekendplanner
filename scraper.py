import os
import requests
from bs4 import BeautifulSoup
import google.genai as genai
from datetime import datetime
import json

# --- 1. CONFIGURATIE ---
# Hier kun je je agenda-items handmatig invullen zolang we de API nog niet hebben
MIJN_AGENDA_DIT_WEEKEND = """
- Vrijdag: Werken tot 18u, daarna rustig koken.
- Zaterdag: Voormiddag boodschappen, namiddag padel (15u-17u).
- Zondag: Bezoek van ouders voor de lunch (4 personen).
"""

INSTRUCTIES = f"""
Jij bent een sterrenchef en planner. 
GEBRUIK DE AGENDA: {MIJN_AGENDA_DIT_WEEKEND}
Focus op: groenten, fruit, vlees, vis en zuivel.
Maak een menu dat past bij de tijdstippen in de agenda.
Antwoord in HTML met duidelijke koppen.
"""

API_KEY = os.environ.get("GEMINI_API_KEY")
client = genai.Client(api_key=API_KEY)

HEADERS = {
    "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/122.0.0.0 Safari/537.36"
}

# --- 2. DE SLIMMERE SCRAPER ---

def scrape_lidl_deep(url):
    if not url: return []
    print(f"Deep scraping: {url}")
    products = []
    try:
        r = requests.get(url, headers=HEADERS, timeout=15)
        soup = BeautifulSoup(r.text, 'html.parser')
        
        # TRICK 1: Zoek naar JSON data in script tags (Lidl verstopt hier vaak zijn producten)
        scripts = soup.find_all('script', type='application/ld+json')
        for script in scripts:
            try:
                data = json.loads(script.string)
                # Als het een lijst met producten is (ItemList)
                if isinstance(data, dict) and 'itemListElement' in data:
                    for item in data['itemListElement']:
                        if 'name' in item:
                            products.append(item['name'])
            except:
                continue

        # TRICK 2: Zoek naar specifieke product-attributen in de HTML
        for el in soup.find_all(attrs={"data-productname": True}):
            products.append(el['data-productname'])

        # TRICK 3: Backup - Zoek naar titels in product-grids
        if not products:
            for item in soup.select('article h3, .ret-o-card__headline'):
                products.append(item.get_text(strip=True))

        return list(set(products))
    except Exception as e:
        print(f"Fout: {e}")
        return []

def get_links():
    offers_url = "https://www.lidl.be/c/nl-BE/aanbiedingen/s10006730"
    try:
        r = requests.get(offers_url, headers=HEADERS, timeout=15)
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
    
    # We scrapen nu 'diep'
    all_items = scrape_lidl_deep(urls.get("week")) + scrape_lidl_deep(urls.get("weekend"))
    
    print(f"--- DEBUG INFO ---")
    print(f"Aantal ECHTE producten gevonden: {len(all_items)}")
    print(f"Eerste 10 producten: {all_items[:10]}")
    
    if len(all_items) > 3:
        # We geven de echte lijst en de agenda aan Gemini
        prompt = f"Producten in promo:\n{all_items}\n\nMaak mijn weekendplan op basis van mijn agenda."
        response = client.models.generate_content(
            model="gemini-2.0-flash", 
            contents=prompt,
            config={'system_instruction': INSTRUCTIES}
        )
        inhoud = response.text
    else:
        inhoud = "Kon geen specifieke producten vinden. De website van Lidl is momenteel lastig te lezen voor de scraper."

    # HTML genereren (zelfde als voorheen)
    nu = datetime.now().strftime("%d-%m-%Y %H:%M")
    with open("index.html", "w", encoding="utf-8") as f:
        f.write(f"<html><body style='font-family:sans-serif; max-width:800px; margin:auto; padding:20px;'><h1>Mijn Weekend Planner</h1><div style='border:1px solid #ddd; padding:20px; border-radius:10px;'>{inhoud}</div><p style='color:grey; font-size:0.8em;'>Update: {nu}</p></body></html>")
