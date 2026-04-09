import os
import requests
from bs4 import BeautifulSoup
import google.genai as genai
from datetime import datetime

# --- CONFIGURATIE ---
SCRAPINGBEE_KEY = os.environ.get("SCRAPINGBEE_API_KEY")
GEMINI_KEY = os.environ.get("GEMINI_API_KEY")

client = genai.Client(api_key=GEMINI_KEY)

def get_lidl_data():
    target_url = "https://www.lidl.be/c/nl-BE/aanbiedingen-deze-week/a10082242"
    print(f"Lidl data ophalen via ScrapingBee...")
    
    # We vragen ScrapingBee om de pagina te laden, JS uit te voeren en de cookies te negeren
    api_url = "https://app.scrapingbee.com/api/v1/"
    params = {
        'api_key': SCRAPINGBEE_KEY,
        'url': target_url,
        'render_js': 'true',          # Cruciaal voor de producten
        'wait_for': '.ret-o-card',    # Wacht tot er minstens één product-kaart verschijnt
        'block_ads': 'true'
    }
    
    try:
        r = requests.get(api_url, params=params, timeout=60)
        if r.status_code == 200:
            soup = BeautifulSoup(r.text, 'html.parser')
            products = []
            
            # We zoeken naar de titels (h3) die in de productkaarten staan
            for item in soup.select('h3'):
                title = item.get_text(strip=True)
                if len(title) > 5 and "Lidl" not in title:
                    products.append(title)
            
            return list(set(products))
        else:
            print(f"ScrapingBee fout: {r.status_code}")
            return []
    except Exception as e:
        print(f"Fout: {e}")
        return []

if __name__ == "__main__":
    found_products = get_lidl_data()
    
    print(f"DEBUG: {len(found_products)} producten gevonden.")
    if found_products:
        print(f"Voorbeelden: {found_products[:5]}")

    # --- GEMINI SECTIE ---
    prompt_data = "\n".join(found_products) if found_products else "Seizoensproducten April"
    
    # Systeem instructie voor de Chef
    instructies = "Jij bent mijn persoonlijke chef. Maak een menu op basis van deze producten (of seizoensproducten als de lijst kort is). Antwoord in HTML."
    
    try:
        response = client.models.generate_content(
            model="gemini-2.0-flash", 
            contents=f"Lidl lijst:\n{prompt_data}\n\nMaak mijn weekendplan.",
            config={'system_instruction': instructies}
        )
        inhoud = response.text
    except Exception as e:
        inhoud = f"Planning mislukt: {e}"

    # HTML opslaan
    nu = datetime.now().strftime("%d-%m-%Y %H:%M")
    with open("index.html", "w", encoding="utf-8") as f:
        f.write(f"<html><body style='font-family:sans-serif; max-width:800px; margin:auto; padding:20px;'><h1>Mijn Weekend Planner</h1><div style='border:1px solid #ddd; padding:20px; border-radius:10px;'>{inhoud}</div><p style='color:grey;'>Update: {nu}</p></body></html>")
