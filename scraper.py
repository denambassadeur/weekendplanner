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
        context = browser.new_context(viewport={'width': 1280, 'height': 1000})
        page = context.new_page()
        
        try:
            # 1. Pagina laden
            page.goto(url, wait_until="domcontentloaded", timeout=60000)
            
            # 2. Cookies accepteren
            try:
                page.wait_for_selector("#onetrust-accept-btn-handler", timeout=5000)
                page.click("#onetrust-accept-btn-handler")
                print("Cookies geaccepteerd!")
                page.wait_for_timeout(2000)
            except:
                print("Geen cookie-banner gevonden.")

            # 3. Wachten tot de product-grid echt zichtbaar is
            # We zoeken naar h3-tags die vaak de titels bevatten
            print("Wachten op product-titels...")
            page.wait_for_selector("h3", timeout=10000)
            
            # 4. Scrollen om alles in te laden
            page.evaluate("window.scrollTo(0, document.body.scrollHeight)")
            page.wait_for_timeout(2000)

            # 5. Playwright de teksten direct laten ophalen (geen BeautifulSoup nodig)
            # We pakken ALLE h3 teksten op de pagina
            raw_titles = page.locator("h3").all_text_contents()
            
            for title in raw_titles:
                t = title.strip()
                # Filter: Geen menu-items of korte ruis
                blacklist = ['lidl', 'service', 'account', 'cookies', 'nieuwsbrief', 'folder']
                if len(t) > 5 and not any(word in t.lower() for word in blacklist):
                    products.append(t)
            
            print(f"Totaal aantal ruwe h3's gevonden: {len(raw_titles)}")

        except Exception as e:
            print(f"Browser fout: {e}")
        
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
