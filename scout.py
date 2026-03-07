import requests
from bs4 import BeautifulSoup
import json
import time
from datetime import datetime
import os
import random
import re
from deep_translator import GoogleTranslator
from git import Repo  # Necesar pentru sync

# --- CONFIGURARE GITHUB ---
PATH_TO_REPO = r"C:\calea\catre\proiectul\tau"  # Pune calea folderului unde ai .git
COMMIT_MESSAGE = "Update Intelligence Feed [Auto]"

def sync_to_github():
    """Urcă fișierele JSON automat pe GitHub."""
    try:
        repo = Repo(PATH_TO_REPO)
        repo.index.add(["intel_data.json", "equipment.json", "casualties.json"])
        repo.index.commit(COMMIT_MESSAGE)
        origin = repo.remote(name='origin')
        origin.push()
        print(f"[{datetime.now().strftime('%H:%M:%S')}] Cloud Sync Successful.")
    except Exception as e:
        print(f"Eroare Sync GitHub: {e}")

def translate_intel(text):
    try:
        if any('\u0400' <= char <= '\u04FF' for char in text):
            return GoogleTranslator(source='auto', target='en').translate(text)
        return text
    except: return text

def scrape_telegram(channel_user):
    url = f"https://t.me/s/{channel_user}"
    headers = {'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36'}
    items = []
    try:
        response = requests.get(url, headers=headers, timeout=15)
        if response.status_code != 200: return items
        soup = BeautifulSoup(response.content, 'html.parser')
        messages = soup.select('.tgme_widget_message')
        for msg in messages:
            try:
                text_area = msg.select_one('.tgme_widget_message_text')
                if not text_area: continue
                raw_text = text_area.get_text(separator=" ", strip=True)
                full_text = translate_intel(raw_text)
                title = full_text[:110].replace('\n', ' ') + "..."
                time_tag = msg.select_one('time')
                time_iso = time_tag.get('datetime') if time_tag and time_tag.has_attr('datetime') else datetime.now().isoformat()
                link_tag = msg.select_one('.tgme_widget_message_date')
                link = link_tag.get('href') if link_tag else f"https://t.me/s/{channel_user}"
                items.append({"titlu": title, "full_text": full_text, "source": f"TG: @{channel_user}", "time": time_iso, "link": link})
            except: continue
    except: pass
    return items

def update_stats_automatically(all_messages):
    equipment_stats = {"Main Battle Tanks": "Scanning...", "Armored Vehicles": "Scanning...", "UAVs / Drones": "Scanning...", "Artillery Systems": "Scanning...", "Air Defense": "Scanning..."}
    combined_text = " ".join([m['full_text'].lower() for m in all_messages[:50]]) 
    e_patterns = {
        "Main Battle Tanks": r"(\d+[.,]?\d*)\s*(?:tanks|t-72|t-90|merkava)",
        "Armored Vehicles": r"(\d+[.,]?\d*)\s*(?:apc|bmp|armored|ifv|namer)",
        "UAVs / Drones": r"(\d+[.,]?\d*)\s*(?:drones|uavs|shahed|quadcopters)",
        "Artillery Systems": r"(\d+[.,]?\d*)\s*(?:artillery|howitzers|m777|grad)",
        "Air Defense": r"(\d+[.,]?\d*)\s*(?:air defense|sam|patriot|iron dome)"
    }
    found_e = False
    for name, pattern in e_patterns.items():
        match = re.search(pattern, combined_text)
        if match:
            equipment_stats[name] = match.group(1)
            found_e = True
    final_e = [{"name": k, "count": v} for k, v in equipment_stats.items()]
    with open("equipment.json", "w", encoding='utf-8') as f: json.dump(final_e, f, indent=4)

    c_match = re.search(r"(\d{2,6}[.,]?\d*)\s*(?:killed|dead|liquidated|casualties|kia|deaths)", combined_text)
    if c_match:
        val = c_match.group(1)
        final_c = [{"name": "Personnel (KIA)", "count": f"{val}"}, {"name": "Wounded in Action", "count": "Updating..."}, {"name": "Prisoners of War", "count": "Updating..."}]
    else:
        final_c = [{"name": "Personnel (KIA)", "count": "Scanning..."}, {"name": "Wounded in Action", "count": "Scanning..."}, {"name": "Prisoners of War", "count": "Scanning..."}]
    with open("casualties.json", "w", encoding='utf-8') as f: json.dump(final_c, f, indent=4)

def process_intel():
    channels = ["BellumActaNews", "middleeastspectator", "intelslava", "Lebanon_Intel"]
    # GEOFENCING: Am păstrat doar locațiile din Orientul Mijlociu
    geo_db = {
        "Gaza": [31.50, 34.46], "Tel Aviv": [32.08, 34.78], "Beirut": [33.89, 35.50],
        "Damascus": [33.51, 36.27], "Haifa": [32.81, 34.98], "Eilat": [29.55, 34.95],
        "Nabatieh": [33.37, 35.48], "Tyre": [33.27, 35.19], "Tehran": [35.68, 51.38],
        "Bandar Abbas": [27.18, 56.28], "Bushehr": [28.92, 50.83], "Chabahar": [25.29, 60.64],
        "Shiraz": [29.59, 52.53], "Kish Island": [26.52, 53.98], "Abu Dhabi": [24.45, 54.37],
        "Dubai": [25.20, 55.27], "Kuwait City": [29.37, 47.97], "Manama": [26.22, 50.58],
        "Doha": [25.28, 51.53], "Hodeidah": [14.79, 42.95], "Baghdad": [33.31, 44.36],
        "Basra": [30.50, 47.81]
    }

    all_new_intel = []
    for channel in channels:
        print(f"[{datetime.now().strftime('%H:%M:%S')}] Intercepting @{channel}...")
        results = scrape_telegram(channel)
        all_new_intel.extend(results)
        time.sleep(1.5)

    if all_new_intel:
        update_stats_automatically(all_new_intel)

    processed_data = []
    for item in all_new_intel:
        search_zone = (item['titlu'] + " " + item['full_text']).lower()
        score_iran = sum(2 for x in ["iran", "hezbollah", "houthi", "hamas", "beirut", "tehran"] if x in search_zone)
        score_israel = sum(2 for x in ["israel", "idf", "mossad", "iaf", "netanyahu"] if x in search_zone)
        item['side'] = "iran" if score_iran > score_israel else "israel"
        item['status'] = "unconfirmed" if any(x in search_zone for x in ["?", "allegedly", "reportedly"]) else "verified"
        
        item['lat'], item['lon'] = None, None 
        found_locations = []
        for city, coords in geo_db.items():
            if city.lower() in search_zone:
                found_locations.append((search_zone.find(city.lower()), coords))
        
        if found_locations:
            found_locations.sort(key=lambda x: x[0])
            best_coords = found_locations[0][1]
            item['lat'] = best_coords[0] + random.uniform(-0.05, 0.05)
            item['lon'] = best_coords[1] + random.uniform(-0.05, 0.05)
        processed_data.append(item)

    existing = []
    if os.path.exists("intel_data.json"):
        with open("intel_data.json", "r", encoding='utf-8') as f:
            try: existing = json.load(f)
            except: existing = []

    combined = { x['titlu']: x for x in existing }
    for new_item in processed_data:
        titlu_nou = new_item['titlu']
        if titlu_nou in combined:
            new_item['time'] = combined[titlu_nou].get('time')
            combined[titlu_nou] = new_item
        else:
            combined[titlu_nou] = new_item

    final = sorted(combined.values(), key=lambda x: str(x.get('time')), reverse=True)[:200]
    with open("intel_data.json", "w", encoding='utf-8') as f:
        json.dump(final, f, indent=4, ensure_ascii=False)
    
    # DUPĂ SALVARE, FACEM SYNC PE GITHUB
    sync_to_github()
    print(f"[{datetime.now().strftime('%H:%M:%S')}] Terminal Sync Complete. DB: {len(final)}")

if __name__ == "__main__":
    while True:
        process_intel()
        time.sleep(120) # 2 minute pauză ca să nu primești ban de la GitHub/Telegram