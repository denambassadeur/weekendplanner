import os
import requests
from bs4 import BeautifulSoup
import google.genai as genai
from datetime import datetime

# --- 1. CONFIGURATIE ---
INSTRUCTIES = """
Jij bent mijn persoonlijke chef. 
Scan de lijst met woorden die ik je geef. 
Als je eten of drinken herkent, maak dan een menu. 
Als je alleen websitenavigatie ziet (zoals 'Jobs', 'Contact'), 
leg dan uit dat de scraper waarschijnlijk de verkeerde data ophaalt.
Antwoord in HTML.
"""

API_KEY = os.environ.get("GEMINI_API_KEY")
client = genai.Client(api_key=API_KEY)

# Extra uitgebreide headers om Lidl te overtuigen dat we een echte browser zijn
HEADERS = {
    "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/122.0.0.0 Safari/537.36",
    "Accept-Language": "nl-BE,nl;q=0.9,en-US;q=0.8,en;q=0.7",
    "Referer": "https://www.google.com/"
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
        return {"week": None, "weekend": None}

def scrape_products(url):
    if not url: 
        return []
    
    print(f"Scrapen van: {url}")
    items = []
    try:
        r = requests.get(url, headers=HEADERS, timeout=15)
        soup = BeautifulSoup(r.text, 'html.parser')
        # We pakken alle koppen, sterke teksten en specifieke product-tags
        for tag in soup.find_all(['h2', 'h3', 'strong', 'span']):
            text = tag.get_text(strip=True)
            if 4 < len(text) < 50:
                items.append(text)
        return list(set(items))
    except Exception as e:
        print(f"Fout tijdens scrapen: {e}")
        return []

def ask_gemini(data_list):
    print("Gemini analyseert de data...")
    raw_text = "\n".join(data_list[:100])
    
    prompt = f"Data van Lidl website:\n{raw_text}\n\nOPDRACHT: Maak een weekendplanning met recepten als je eten vindt. Zo niet, rapporteer wat je wel ziet."
    
    try:
        response = client.models.generate_content(
            model="gemini-2.0-flash", 
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
    
    # DEBUG OUTPUT voor de GitHub logs
    print(f"--- DEBUG INFO ---")
    print(f"Aantal items gevonden: {len(totaal_items)}")
    if totaal_items:
        print(f"Eerste 20 items: {totaal_items[:20]}")
    else:
        print("WAARSCHUWING: Geen tekst gevonden!")
    print(f"------------------")

    if len(totaal_items) > 5:
        inhoud = ask_gemini(totaal_items)
    else:
        inhoud = "De scraper kon geen informatie vinden. Lidl blokkeert mogelijk de toegang."

    nu = datetime.now().strftime("%d-%m-%Y %H:%M")
    
    html_output = f"""
    <html>
    <head><title>Weekend Planner</title>
    <style>
        body{{font-family:sans-serif; max-width:800px; margin:40px auto; padding:20px; background:#f4f7f6; color:#333; line-height:1.6;}}
        .card{{background:white; padding:30px; border-radius:12px; box-shadow:0 4px 10px rgba(0,0,0,0.1);}}
        h1{{color:#0050aa; border-bottom: 2px solid #0050aa; padding-bottom:10px;}}
    </style>
    </head>
    <body>
        <div class="card">
            <h1>🍴 Mijn Weekend Planner</h1>
            {inhoud}
        </div>
        <p style="text-align:center; color:grey; margin-top:30px; font-size:0.8em;">Update: {nu}</p>
    </body>
    </html>
    """
    
    with open("index.html", "w", encoding="utf-8") as f:
        f.write(html_output)
    print("Klaar!")
