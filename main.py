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
def home():
    return "Бот активен"

def run():
    app.run(host='0.0.0.0', port=8080)

def keep_alive():
    t = Thread(target=run)
    t.start()

GAME_DATA = {
    "BRAZILIAN SPYDER": {"name": "Steal a brainrot", "universe_id": 6144841331},
    "Uplift Games": {"name": "Adopt me", "universe_id": 231221121},
    "Wave of Brainrots": {"name": "Tsunami brainrots", "universe_id": 6344131331},
    "Nikilis": {"name": "MM2", "universe_id": 66654135},
    "The Garden Game": {"name": "GAG", "universe_id": 5834131131},
    "KizmoTek Studio": {"name": "War tycoon", "universe_id": 2686721523},
    "Gamer Robot Inc": {"name": "Blox fruits", "universe_id": 444227218}
}

def get_extra_info(u_id, cookies):
    """Получает Premium, дату регистрации и друзей"""
    try:
        # Инфо о пользователе (дата регистрации и премиум)
        u_data = requests.get(f"https://users.roblox.com/v1/users/{u_id}").json()
        reg_date = datetime.strptime(u_data['created'], "%Y-%m-%dT%H:%M:%S.%fZ").strftime("%d.%m.%Y")
        has_premium = "Да ✅" if u_data.get('hasPremium', False) else "Нет ❌"
        
        # Друзья
        f_data = requests.get(f"https://friends.roblox.com/v1/users/{u_id}/friends/count").json()
        f_count = f_data.get('count', 0)
        
        return reg_date, has_premium, f_count
    except:
        return "Неизвестно", "Неизвестно", 0

def get_recent_places(cookies):
    try:
        url = "https://games.roblox.com/v1/games/list?model.maxRows=10&model.pageContext.sortName=ContinueWatching"
        res = requests.get(url, cookies=cookies, timeout=5).json()
        games = [g['name'] for g in res.get('games', [])]
        return "\n • " + "\n • ".join(games) if games else "Нет недавних заходов"
    except: return "Скрыто"

def get_created_places(cookies):
    try:
        url = "https://develop.roblox.com/v1/user/universes?limit=10&sortOrder=Desc"
        res = requests.get(url, cookies=cookies, timeout=5).json()
        places = [g['name'] for g in res.get('data', [])]
        return "\n • " + "\n • ".join(places) if places else "Нет созданных игр"
    except: return "Ошибка доступа"

def get_game_badges(u_id, universe_id, cookies):
    try:
        url = f"https://badges.roblox.com/v1/users/{u_id}/universes/{universe_id}/badges?limit=5&sortOrder=Desc"
        res = requests.get(url, cookies=cookies, timeout=5).json()
        badges = [b['name'] for b in res.get('data', [])]
        return " (🏆: " + ", ".join(badges) + ")" if badges else " (Нет бейджей)"
    except: return ""

def get_last_online(u_id, cookies):
    try:
        res = requests.post("https://presence.roblox.com/v1/presence/last-online", 
                            json={"userIds": [u_id]}, cookies=cookies, timeout=5).json()
        last_online_str = res['lastOnlineTimestamps'][0]['lastOnline']
        dt = datetime.strptime(last_online_str, "%Y-%m-%dT%H:%M:%S.%fZ")
        return dt.strftime("%d.%m.%Y %H:%M")
    except: return "Неизвестно"

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
        
        last_time = get_last_online(u_id, cookies)
        recent = get_recent_places(cookies)
        created = get_created_places(cookies)
        robux = requests.get(f"https://economy.roblox.com/v1/users/{u_id}/currency", cookies=cookies).json().get('robux', 0)
        reg_date, premium, friends = get_extra_info(u_id, cookies)
        
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
            "name": u_name, "id": u_id, "robux": robux, "details": details_text or "Трат нет.\n",
            "last_time": last_time, "recent": recent, "created": created, "spent": total_spent, 
            "reg_date": reg_date, "premium": premium, "friends": friends,
            "cookie": cookie, "status": "ok"
        }
    except: return {"status": "error"}

def format_output(res):
    return (
        f"👤 **Аккаунт:** {res['name']} (ID: {res['id']})\n"
        f"🗓 **Регистрация:** {res['reg_date']}\n"
        f"🌟 **Premium:** {res['premium']}\n"
        f"👥 **Друзей:** {res['friends']}\n"
        f"🕒 **Был в сети:** {res['last_time']}\n"
        f"💰 **Баланс:** {res['robux']} R$\n\n"
        f"🕹 **ПОСЛЕДНИЕ ИГРАЛ:** {res['recent']}\n\n"
        f"🛠 **СОЗДАННЫЕ ИГРЫ:** {res['created']}\n\n"
        f"💸 **ТРАТЫ И БЕЙДЖИ:**\n{res['details']}"
        f"--- Всего по списку: {res['spent']} R$ ---\n\n"
        f"🍪 **КУКИ:**\n`{res['cookie']}`\n"
        f"{'='*30}\n"
    )

@bot.message_handler(commands=['start'])
def start(message):
    text = (
        "👋 **Привет! Я чекаю аккаунты Roblox 24/7.**\n\n"
        "📥 **Отправь мне куки текстом или .txt файлом**, и я выдам тебе:\n"
        "• Баланс робуксов и Premium\n"
        "• Дату регистрации и друзей\n"
        "• Траты в популярных плейсах\n"
        "• Списки последних и созданных игр"
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
            bot.send_message(message.chat.id, f"⌛ Начинаю чек {len(lines)} строк...")
            results = [format_output(res) for l in lines if l.strip() and (res := check_cookie(l))['status'] == 'ok']
            if results:
                buf = io.BytesIO("".join(results).encode('utf-8'))
                buf.name = "checked_results.txt"
                bot.send_document(message.chat.id, buf)
            else:
                bot.send_message(message.chat.id, "❌ Валидных аккаунтов не найдено.")
    except Exception as e: print(f"Ошибка: {e}")

if __name__ == '__main__':
    keep_alive()
    bot.infinity_polling()
