import os
import requests
from bs4 import BeautifulSoup
import google.genai as genai
from datetime import datetime

# --- 1. CONFIGURATIE ---
INSTRUCTIES = """
Jij bent mijn persoonlijke chef. 
Zelfs als de lijst met producten rommelig is, probeer je er eetbare zaken uit te vissen.
Als je echt niets eetbaars vindt, leg dan kort uit wat voor soort tekst je wél hebt ontvangen (bijv. "Ik zie alleen menu-items zoals 'Jobs' en 'Contact'").
Antwoord in HTML.
"""

API_KEY = os.environ.get("GEMINI_API_KEY")
client = genai.Client(api_key=API_KEY)

HEADERS = {
    "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36"
}

# --- 2. FUNCTIES ---

def get_links():
    offers_url = "https://www.lidl.be/c/nl-BE/aanbiedingen/s10006730"
    print("Zoeken naar actuele links op Lidl.be...")
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
        return {}

def scrape_products(url):
    if not url: return ""
    print(f"Scrapen van: {url}")
    items = []
    try:
        r = requests.get(url, headers=HEADERS, timeout=15)
        soup = BeautifulSoup(r.text, 'html.parser')
        # We pakken alles wat tekst is in koppen en sterke tags
        for tag in soup.find_all(['h2', 'h3', 'strong', 'span']):
            text = tag.get_text(strip=True)
            if 4 < len(text) < 50:
                items.append(text)
        return list(set(items))
    except:
        return []

def ask_gemini(data_list):
    print("Gemini analyseert de data...")
    # We maken een tekstblok van de eerste 100 items om te besparen op tokens
    raw_text = "\n".join(data_list[:100])
    
    prompt = f"""
    Hier is de data van de Lidl website:
    {raw_text}

    OPDRACHT:
    1. Zoek naar promoties van eten of drinken.
    2. Als je ze vindt: maak een weekendplanning met recepten (HTML).
    3. Als je GEEN eten vindt: vertel me wat voor soort informatie je wel ziet in de lijst.
    """
    
    try:
        response = client.models.generate_content(
            model="gemini-2.5-flash", 
            contents=prompt,
            config={'system_instruction': INSTRUCTIES}
        )
        return response.text
    except Exception as e:
        return f"Gemini Fout: {e}"

# --- 3. EXECUTIE ---

if __name__ == "__main__":
    urls = get_links()
    
    items_week = scrape_products(urls.get("week"))
    items_weekend = scrape_products(urls.get("weekend"))
    totaal_items = items_week + items_weekend
    
    # DEBUG: Print de eerste 15 items in de GitHub logs
    print(f"DEBUG - Totaal items gevonden: {len(totaal_items)}")
    print(f"DEBUG - Eerste 15 items: {totaal_items[:15]}")

    if len(totaal_items) > 5:
        inhoud = ask_gemini(totaal_items)
    else:
        inhoud = "De scraper vond te weinig tekst op de pagina. Waarschijnlijk blokkeert Lidl de toegang voor bots."

    nu = datetime.now().strftime("%d-%m-%Y %H:%M")
    
    html_output = f"""
    <html>
    <head><title>Weekend Planner</title>
    <style>body{{font-family:sans-serif; max-width:800px; margin:40px auto; padding:20px; background:#f4f7f6;}}
    .card{{background:white; padding:30px; border-radius:12px; box-shadow:0 4px 10px rgba(0,0,0,0.1);}}</style>
    </head>
    <body>
        <div class="card">
            <h1>🍴 Mijn Weekend Planner</h1>
            {inhoud}
        </div>
        <p style="text-align:center; color:grey;">Laatste update: {nu}</p>
    </body>
    </html>
    """
    
    with open("index.html", "w", encoding="utf-8") as f:
        f.write(html_output)
