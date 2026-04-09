import os
from playwright.sync_api import sync_playwright
from bs4 import BeautifulSoup
import google.genai as genai
from datetime import datetime

# --- CONFIGURATIE ---
API_KEY = os.environ.get("GEMINI_API_KEY")
client = genai.Client(api_key=API_KEY)

INSTRUCTIES = "Jij bent een culinaire assistent. Maak een weekendmenu op basis van de gevonden Lidl-producten. Antwoord in HTML."

def scrape_lidl_with_browser(url):
    if not url: return []
    print(f"Browser opstarten voor: {url}")
    
    products = []
    with sync_playwright() as p:
        # We gebruiken 'firefox' of 'webkit' als alternatief als chromium te veel op een bot lijkt
        browser = p.chromium.launch(headless=True)
        context = browser.new_context(
            viewport={'width': 1280, 'height': 800},
            user_agent="Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/122.0.0.0 Safari/537.36"
        )
        page = context.new_page()
        
        try:
            # 1. Ga naar de pagina
            page.goto(url, wait_until="domcontentloaded", timeout=60000)
            print("Pagina geladen, op zoek naar de cookie-banner...")

            # 2. Klik op 'Alle cookies accepteren' (Lidl gebruikt vaak OneTrust)
            # We zoeken naar de knop met de tekst 'Accepteren' of een specifiek ID
            try:
                # We wachten max 5 seconden op de cookieknop
                cookie_button = page.wait_for_selector("#onetrust-accept-btn-handler", timeout=5000)
                if cookie_button:
                    cookie_button.click()
                    print("Cookies geaccepteerd!")
                    page.wait_for_timeout(2000) # Even wachten tot de banner weg is
            except:
                print("Geen standaard cookie-banner gevonden, we gaan door...")

            # 3. Scrollen om 'lazy loading' te activeren
            for _ in range(5):
                page.mouse.wheel(0, 1000)
                page.wait_for_timeout(500)

            # 4. Nu de echte data pakken
            print("Producten verzamelen...")
            # We kijken breder naar titels binnen de 'product-grid'
            content = page.content()
            soup = BeautifulSoup(content, 'html.parser')
            
            # We zoeken naar h3's die echt bij een product horen
            for card in soup.find_all(['article', 'div'], class_=lambda x: x and 'product' in x.lower()):
                title_el = card.find('h3')
                if title_el:
                    title = title_el.get_text(strip=True)
                    if len(title) > 3 and "Lidl" not in title:
                        products.append(title)

            # Als backup: alle h3's die geen menu-items zijn
            if not products:
                for h3 in soup.find_all('h3'):
                    t = h3.get_text(strip=True)
                    if len(t) > 5 and t not in ['Cookielijst', 'Social Media', 'Service']:
                        products.append(t)

        except Exception as e:
            print(f"Fout: {e}")
        
        browser.close()
    
    return list(set(products))
# --- EXECUTIE ---
if __name__ == "__main__":
    # We richten ons direct op de hoofdpagina van de aanbiedingen
    target_url = "https://www.lidl.be/c/nl-BE/aanbiedingen-deze-week/a10082242"
    
    found_products = scrape_lidl_with_browser(target_url)
    
    print(f"--- DEBUG ---")
    print(f"Aantal producten gevonden met Playwright: {len(found_products)}")
    print(f"Eerste 5: {found_products[:5]}")
    
    # Gemini aanroepen
    try:
        prompt_data = "\n".join(found_products) if found_products else "Geen specifieke data"
        response = client.models.generate_content(
            model="gemini-2.5-flash", 
            contents=f"Lidl Producten:\n{prompt_data}\n\nMaak mijn weekendplan.",
            config={'system_instruction': INSTRUCTIES}
        )
        inhoud = response.text
    except Exception as e:
        inhoud = f"Gemini kon niet plannen: {e}"

    # HTML Opslaan (zoals voorheen)
    nu = datetime.now().strftime("%d-%m-%Y %H:%M")
    with open("index.html", "w", encoding="utf-8") as f:
        f.write(f"<html><body><h1>Weekend Planner</h1><div>{inhoud}</div><p>Update: {nu}</p></body></html>")
