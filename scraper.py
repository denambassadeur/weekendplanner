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
        browser = p.chromium.launch(headless=True)
        # We geven de browser een specifieke taal en regio mee
        context = browser.new_context(locale="nl-BE")
        page = context.new_page()
        
        try:
            # We veranderen 'networkidle' naar 'domcontentloaded' (sneller)
            # En we verhogen de timeout naar 60 seconden voor de zekerheid
            page.goto(url, wait_until="domcontentloaded", timeout=60000)
            
            # We wachten expliciet 5 seconden extra voor de JavaScript producten
            print("Pagina geladen, even wachten op de producten...")
            page.wait_for_timeout(5000)
            
            # Scroll omlaag om alles te triggeren
            page.evaluate("window.scrollTo(0, document.body.scrollHeight)")
            page.wait_for_timeout(2000)

            content = page.content()
            soup = BeautifulSoup(content, 'html.parser')
            
            # Dezelfde selectors als voorheen
            selectors = ['h3.ret-o-card__headline', '.ret-o-product-tile__title', 'h3']
            for selector in selectors:
                for el in soup.select(selector):
                    text = el.get_text(strip=True)
                    if len(text) > 5 and "Lidl" not in text:
                        products.append(text)
                        
        except Exception as e:
            print(f"Waarschuwing tijdens browser-sessie: {e}")
            # We proberen alsnog de producten te pakken die er wél al staan
            content = page.content()
            soup = BeautifulSoup(content, 'html.parser')
            for el in soup.select('h3'):
                products.append(el.get_text(strip=True))
        
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
