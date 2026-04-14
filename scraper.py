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
    if not SCRAPINGBEE_KEY:
        print("FOUT: SCRAPINGBEE_API_KEY niet gevonden in omgeving!")
        return []

    target_url = "https://www.lidl.be/c/nl-BE/aanbiedingen-deze-week/a10082242"
    print(f"Lidl data ophalen via ScrapingBee...")
    
    api_url = "https://app.scrapingbee.com/api/v1/"
    params = {
        'api_key': SCRAPINGBEE_KEY,
        'url': target_url,
        'render_js': 'true',
        'wait_for': 'h3', # We wachten simpelweg op de eerste de beste kop
        'block_ads': 'true',
        'premium_proxy': 'true', # Sommige retailers vereisen dit
        'country_code': 'be'     # Forceer Belgische servers
    }
    
    try:
        r = requests.get(api_url, params=params, timeout=60)
        
        if r.status_code == 200:
            soup = BeautifulSoup(r.text, 'html.parser')
            products = []
            # We zoeken breed naar alle h3's en h2's
            for item in soup.find_all(['h3', 'h2']):
                title = item.get_text(strip=True)
                if len(title) > 5 and "Lidl" not in title:
                    products.append(title)
            return list(set(products))
        else:
            # Dit laat ons de ECHTE foutboodschap van ScrapingBee zien
            print(f"ScrapingBee Fout {r.status_code}: {r.text}")
            return []
    except Exception as e:
        print(f"Netwerkfout: {e}")
        return []

if __name__ == "__main__":
    found_products = get_lidl_data()
    
    print(f"DEBUG: {len(found_products)} producten gevonden.")
    
    # We laten Gemini altijd iets genereren, zelfs bij 0 producten
    prompt_data = "\n".join(found_products) if found_products else "Gebruik seizoensproducten van april (asperges, aardbeien, lam)."
    
    instructies = "Jij bent een topchef. Maak een weekendmenu op basis van de input (of seizoensproducten). Antwoord in HTML."
    
    try:
        response = client.models.generate_content(
            model="gemini-3.1-flash-lite-preview", # Of gebruik gemini-1.5-flash voor snelheid
            contents=f"Data:\n{prompt_data}\n\nMaak mijn weekendplan.",
            config={'system_instruction': instructies}
        )
        inhoud = response.text
    except Exception as e:
        inhoud = f"Gemini error: {e}"

    # HTML opslaan
    nu = datetime.now().strftime("%d-%m-%Y %H:%M")
    with open("index.html", "w", encoding="utf-8") as f:
        f.write(f"<html><body style='font-family:sans-serif; max-width:800px; margin:auto; padding:20px; line-height:1.6;'>")
        f.write(f"<h1>🍴 Weekend Planner</h1><div style='background:white; border:1px solid #ddd; padding:20px; border-radius:12px;'>{inhoud}</div>")
        f.write(f"<p style='color:grey; font-size:0.8em; margin-top:20px;'>Laatste update: {nu}</p></body></html>")
    print("Klaar!")
