import telebot
import requests
import io
import re
from datetime import datetime
from flask import Flask
from threading import Thread

# === НАСТРОЙКИ ===
TOKEN = '8526516729:AAHxx09k48kWRk0U7q2AcFSCmEdg3TDcfEw'
bot = telebot.TeleBot(TOKEN)

app = Flask('')
@app.route('/')
def home(): return "Бот работает"

def run(): app.run(host='0.0.0.0', port=8080)
def keep_alive(): Thread(target=run).start()

def get_detailed_stats(u_id, cookies, headers):
    """Сбор данных с минимальным риском для куки"""
    stats = {"age": 0, "voice": "Нет ❌", "pending": 0, "email": "❌", "rap": 0}
    try:
        # Пендинг и Баланс (в одном запросе часто безопаснее)
        summary = requests.get(
            f"https://economy.roblox.com/v2/users/{u_id}/transaction-totals?timeFrame=Month&transactionType=Summary",
            cookies=cookies, headers=headers, timeout=5
        ).json()
        stats["pending"] = summary.get('pendingRobux', 0)

        # Почта
        email_data = requests.get("https://accountsettings.roblox.com/v1/email", cookies=cookies, headers=headers, timeout=5).json()
        if email_data.get('verified'): stats["email"] = "Да ✅"

        # Voice Chat
        v_req = requests.get("https://voice.roblox.com/v1/settings/is-voice-enabled", cookies=cookies, headers=headers, timeout=5).json()
        if v_req.get('isVoiceEnabled'): stats["voice"] = "Да ✅"

        # RAP
        inv = requests.get(f"https://inventory.roblox.com/v1/users/{u_id}/assets/collectibles?limit=100", cookies=cookies, headers=headers, timeout=5).json()
        stats["rap"] = sum(item.get('recentAveragePrice', 0) for item in inv.get('data', []))
    except: pass
    return stats

def extract_cookie(text):
    match = re.search(r"(_\|WARNING:-DO-NOT-SHARE-THIS\..+)", text)
    return match.group(1).strip() if match else None

def check_cookie(raw_text):
    cookie = extract_cookie(raw_text)
    if not cookie: return {"status": "invalid"}
    
    cookies = {".ROBLOSECURITY": cookie}
    # Имитируем заголовки мобильного приложения Roblox (они стабильнее)
    headers = {
        "User-Agent": "RobloxApp/1.0 (iPhone; iOS 15.0; Scale/2.00)",
        "Accept": "application/json",
        "Referer": "https://www.roblox.com/"
    }
    
    try:
        # Главная проверка (Auth)
        auth_req = requests.get("https://users.roblox.com/v1/users/authenticated", cookies=cookies, headers=headers, timeout=10)
        if auth_req.status_code != 200: return {"status": "invalid"}
        
        user_info = auth_req.json()
        u_id, u_name = user_info['id'], user_info['name']
        
        # Основная инфа
        profile = requests.get(f"https://users.roblox.com/v1/users/{u_id}", headers=headers).json()
        created_dt = datetime.strptime(profile['created'], "%Y-%m-%dT%H:%M:%S.%fZ")
        age = (datetime.now() - created_dt).days
        
        # Валюта
        robux = requests.get(f"https://economy.roblox.com/v1/users/{u_id}/currency", cookies=cookies, headers=headers).json().get('robux', 0)
        
        # Расширенная инфа
        adv = get_detailed_stats(u_id, cookies, headers)
        
        return {
            "status": "ok", "name": u_name, "id": u_id, "robux": robux,
            "age": age, "voice": adv["voice"], "pending": adv["pending"], 
            "rap": adv["rap"], "email": adv["email"], "cookie": cookie
        }
    except: return {"status": "error"}

def format_output(res):
    return (
        f"👤 Аккаунт: {res['name']} (ID: {res['id']})\n"
        f"🎂 Возраст: {res['age']} дней\n"
        f"📧 Почта: {res['email']} | 🎤 Voice: {res['voice']}\n"
        f"💰 Баланс: {res['robux']} R$ (+{res['pending']} Pending)\n"
        f"💎 Ценность (RAP): {res['rap']} R$\n\n"
        f"🍪 КУКИ:\n`{res['cookie']}`\n"
        f"{'='*30}\n"
    )

@bot.message_handler(commands=['start'])
def start(message):
    bot.reply_to(message, "👋 Привет! Пришли куки или файл. Проверка стала безопаснее.")

@bot.message_handler(content_types=['text', 'document'])
def handle(message):
    try:
        if message.content_type == 'text' and len(message.text) > 100:
            res = check_cookie(message.text)
            if res['status'] == 'ok':
                bot.send_message(message.chat.id, format_output(res), parse_mode="Markdown")
            else:
                bot.send_message(message.chat.id, "❌ Куки невалиден или заблокирован защитой.")
        
        elif message.content_type == 'document':
            file_info = bot.get_file(message.document.file_id)
            content = bot.download_file(file_info.file_path).decode('utf-8', errors='ignore')
            lines = [l.strip() for l in content.splitlines() if l.strip()]
            
            bot.send_message(message.chat.id, f"⌛ Чек {len(lines)} строк...")
            results = []
            for l in lines:
                res = check_cookie(l)
                if res['status'] == 'ok': results.append(format_output(res))
            
            if results:
                buf = io.BytesIO("".join(results).encode('utf-8'))
                buf.name = "results.txt"
                bot.send_document(message.chat.id, buf)
            else:
                bot.send_message(message.chat.id, "❌ Валид не найден.")
    except Exception as e:
        print(f"Error: {e}")

if __name__ == '__main__':
    keep_alive()
    bot.infinity_polling()
