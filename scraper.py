import os
import requests
from bs4 import BeautifulSoup
import google.genai as genai
from datetime import datetime
import re
import json

# --- 1. CONFIGURATIE ---
MIJN_AGENDA = """
- Vrijdag: Werken tot 18u.
- Zaterdag: Padel (15u-17u).
- Zondag: Ouders komen lunchen (4 personen).
"""

INSTRUCTIES = f"""
Jij bent een culinaire assistent. 
Agenda: {MIJN_AGENDA}
TAAK:
1. Scan de lijst met producten. 
2. Als je specifieke promoties ziet, gebruik deze in je menu.
3. Als de lijst leeg is, maak dan een 'Chef's Surprise' menu met seizoensproducten van April (asperges, lam, etc.).
4. Antwoord in HTML.
"""

API_KEY = os.environ.get("GEMINI_API_KEY")
client = genai.Client(api_key=API_KEY)

HEADERS = {
    "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/123.0.0.0 Safari/537.36",
    "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,image/avif,image/webp,*/*;q=0.8"
}

# --- 2. DE INTELLIGENTE SCRAPER ---

def scrape_lidl_intelligent(url):
    if not url: return []
    print(f"Deep scraping op: {url}")
    found_products = []
    try:
        r = requests.get(url, headers=HEADERS, timeout=15)
        html_content = r.text
        
        # METHODE A: Zoek naar 'fullTitle' in de Javascript data (Lidl's favoriete plek)
        titles = re.findall(r'"fullTitle":"([^"]+)"', html_content)
        found_products.extend(titles)
        
        # METHODE B: Zoek naar 'name' in JSON-LD objecten
        names = re.findall(r'"name":"([^"]+)"', html_content)
        found_products.extend(names)

        # Opschonen: we negeren woorden die te kort zijn of typische menu-items
        blacklist = ["Lidl", "Menu", "Zoeken", "Winkels", "Jobs", "Contact", "Cookie"]
        cleaned = []
        for p in found_products:
            if len(p) > 5 and not any(b in p for b in blacklist):
                cleaned.append(p)
        
        return list(set(cleaned))
    except Exception as e:
        print(f"Scrape fout: {e}")
        return []

def get_links():
    try:
        r = requests.get("https://www.lidl.be/c/nl-BE/aanbiedingen/s10006730", headers=HEADERS, timeout=15)
        soup = BeautifulSoup(r.text, 'html.parser')
        links = {"week": None, "weekend": None}
        for a in soup.find_all('a', href=True):
            if "aanbiedingen-deze-week" in a['href']:
                links["week"] = "https://www.lidl.be" + a['href']
            if "weekenddeals" in a['href']:
                links["weekend"] = "https://www.lidl.be" + a['href']
        return links
    except:
        return {"week": None, "weekend": None}

# --- 3. DE EXECUTIE ---

if __name__ == "__main__":
    urls = get_links()
    
    # We gebruiken hier de juiste functienaam: scrape_lidl_intelligent
    week_products = scrape_lidl_intelligent(urls.get("week"))
    weekend_products = scrape_lidl_intelligent(urls.get("weekend"))
    all_products = list(set(week_products + weekend_products))
    
    print(f"--- DEBUG INFO ---")
    print(f"Aantal ECHTE producten gevonden: {len(all_products)}")
    if all_products:
        print(f"Voorbeeld: {all_products[:5]}")
    
    # Gemini aanroepen
    try:
        prompt_data = "\n".join(all_products) if all_products else "GEEN_DATA"
        response = client.models.generate_content(
            model="gemini-2.5-flash", 
            contents=f"Lidl Data:\n{prompt_data}\n\nMaak mijn weekendplan.",
            config={'system_instruction': INSTRUCTIES}
        )
        inhoud = response.text
    except Exception as e:
        if "429" in str(e):
            inhoud = "De API is even moe (Quota bereikt). Wacht 15 minuutjes!"
        else:
            inhoud = f"Foutje bij Gemini: {e}"

    # HTML genereren
    nu = datetime.now().strftime("%d-%m-%Y %H:%M")
    with open("index.html", "w", encoding="utf-8") as f:
        f.write(f"<html><body style='font-family:sans-serif; max-width:800px; margin:auto; padding:20px;'><h1>Mijn Weekend Planner</h1><div style='border:1px solid #ddd; padding:20px; border-radius:10px;'>{inhoud}</div><p style='color:grey; font-size:0.8em;'>Update: {nu}</p></body></html>")
    print("Done!")
