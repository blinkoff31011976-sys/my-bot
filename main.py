import os
import sqlite3
import threading
from http.server import HTTPServer, BaseHTTPRequestHandler
import telebot
from telebot import types
import requests

# --- 1. ИНИЦИАЛИЗАЦИЯ И НАСТРОЙКА ---
BOT_TOKEN = os.environ.get('BOT_TOKEN', '')
GEMINI_KEY = os.environ.get('GEMINI_API_KEY', '')

bot = telebot.TeleBot(BOT_TOKEN)

# --- 2. БАЗА ДАННЫХ SQLITE 💾 ---
def init_db():
    try:
        conn = sqlite3.connect('bot_database.db')
        cursor = conn.cursor()
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS users (
                user_id INTEGER PRIMARY KEY,
                username TEXT,
                first_name TEXT,
                query_count INTEGER DEFAULT 0
            )
        ''')
        conn.commit()
        conn.close()
    except Exception as e:
        print(f"Ошибка БД (init): {e}", flush=True)

def save_user(user_id, username, first_name):
    try:
        conn = sqlite3.connect('bot_database.db')
        cursor = conn.cursor()
        cursor.execute('''
            INSERT INTO users (user_id, username, first_name, query_count)
            VALUES (?, ?, ?, 0)
            ON CONFLICT(user_id) DO UPDATE SET
                username = excluded.username,
                first_name = excluded.first_name
        ''', (user_id, username, first_name))
        conn.commit()
        conn.close()
    except Exception as e:
        print(f"Ошибка БД (save): {e}", flush=True)

def increment_queries(user_id):
    try:
        conn = sqlite3.connect('bot_database.db')
        cursor = conn.cursor()
        cursor.execute('''
            UPDATE users SET query_count = query_count + 1 WHERE user_id = ?
        ''', (user_id,))
        conn.commit()
        conn.close()
    except Exception as e:
        print(f"Ошибка БД (increment): {e}", flush=True)

def get_stats(user_id):
    try:
        conn = sqlite3.connect('bot_database.db')
        cursor = conn.cursor()
        cursor.execute('SELECT query_count FROM users WHERE user_id = ?', (user_id,))
        row = cursor.fetchone()
        conn.close()
        return row[0] if row else 0
    except Exception as e:
        print(f"Ошибка БД (stats): {e}", flush=True)
        return 0

# Инициализация БД
init_db()

# --- 3. КЛАВИАТУРА И КОМАНДЫ ⌨️ ---
def get_main_keyboard():
    markup = types.ReplyKeyboardMarkup(resize_keyboard=True)
    markup.row('📊 Статистика', 'ℹ️ О боте')
    markup.row('❓ Помощь')
    return markup

@bot.message_handler(commands=['start'])
def send_welcome(message):
    save_user(message.from_user.id, message.from_user.username, message.from_user.first_name)
    bot.reply_to(
        message,
        f"Привет, {message.from_user.first_name}! 🚀\n"
        "Я бот с интеграцией Google Gemini. Задайте мне любой вопрос!",
        reply_markup=get_main_keyboard()
    )

@bot.message_handler(func=lambda m: m.text == '📊 Статистика')
def show_stats(message):
    count = get_stats(message.from_user.id)
    bot.reply_to(message, f"📈 Вы отправили запросов: {count}")

@bot.message_handler(func=lambda m: m.text == 'ℹ️ О боте')
def about_bot(message):
    bot.reply_to(message, "🤖 Этот бот работает на базе модели Gemini 1.5 Flash.")

@bot.message_handler(func=lambda m: m.text == '❓ Помощь')
def help_info(message):
    bot.reply_to(message, "💡 Напишите любой вопрос в чат, и бот ответит на него.")

# --- 4. ОБРАБОТКА ИИ-ЗАПРОСОВ (ПРЯМОЙ HTTP-ЗАПРОС) 🤖 ---
@bot.message_handler(func=lambda message: True)
def handle_ai_request(message):
    save_user(message.from_user.id, message.from_user.username, message.from_user.first_name)

    if not GEMINI_KEY:
        bot.reply_to(message, "⚠️ Переменная GEMINI_API_KEY не найдена в Render!")
        return

    status_msg = bot.reply_to(message, "🧠 Думаю...")

    try:
        # Прямой запрос к REST API Google Gemini
        url = f"https://generativelanguage.googleapis.com/v1beta/models/gemini-1.5-flash:generateContent?key={GEMINI_KEY}"
        headers = {'Content-Type': 'application/json'}
        payload = {
            "contents": [{
                "parts": [{"text": message.text}]
            }]
        }
        
        response = requests.post(url, headers=headers, json=payload, timeout=15)
        data = response.json()
        
        if response.status_code == 200:
            try:
                answer = data['candidates'][0]['content']['parts'][0]['text']
                increment_queries(message.from_user.id)
                bot.edit_message_text(answer, chat_id=status_msg.chat_id, message_id=status_msg.message_id)
            except (KeyError, IndexError):
                bot.edit_message_text("⚠️ Google вернул ответ в непривычном формате.", chat_id=status_msg.chat_id, message_id=status_msg.message_id)
        else:
            error_details = data.get('error', {}).get('message', response.text)
            bot.edit_message_text(f"❌ Ошибка Google API ({response.status_code}): {error_details}", chat_id=status_msg.chat_id, message_id=status_msg.message_id)

    except requests.exceptions.Timeout:
        bot.edit_message_text("❌ Превышено время ожидания ответа от сервера Google.", chat_id=status_msg.chat_id, message_id=status_msg.message_id)
    except Exception as e:
        bot.edit_message_text(f"❌ Ошибка приложения: {e}", chat_id=status_msg.chat_id, message_id=status_msg.message_id)

# --- 5. СЕРВЕР ДЛЯ RENDER 🌐 ---
class HealthCheckHandler(BaseHTTPRequestHandler):
    def do_GET(self):
        self.send_response(200)
        self.end_headers()
        self.wfile.write(b"Bot is alive!")

def run_http_server():
    port = int(os.environ.get("PORT", 8080))
    server = HTTPServer(('0.0.0.0', port), HealthCheckHandler)
    server.serve_forever()

if __name__ == '__main__':
    threading.Thread(target=run_http_server, daemon=True).start()
    print("Бот запущен...", flush=True)
    bot.infinity_polling()
