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
        # Start een onzichtbare Chrome browser
        browser = p.chromium.launch(headless=True)
        page = browser.new_page()
        
        # Ga naar de pagina en wacht tot hij geladen is
        page.goto(url, wait_until="networkidle")
        
        # Scroll een paar keer naar beneden om 'lazy loading' producten te activeren
        for _ in range(3):
            page.mouse.wheel(0, 2000)
            page.wait_for_timeout(1000)

        # Haal de gerenderde HTML op
        content = page.content()
        soup = BeautifulSoup(content, 'html.parser')
        
        # Zoek naar de echte producttitels
        # Lidl gebruikt in 2026 vaak deze classes
        selectors = [
            'h3.ret-o-card__headline', 
            '.ret-o-product-tile__title',
            'h3'
        ]
        
        for selector in selectors:
            for el in soup.select(selector):
                text = el.get_text(strip=True)
                if len(text) > 5 and "Lidl" not in text:
                    products.append(text)
        
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
