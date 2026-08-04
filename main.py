import os
import sqlite3
import threading
from http.server import HTTPServer, BaseHTTPRequestHandler
import telebot
from telebot import types
import google.generativeai as genai

# --- 1. ИНИЦИАЛИЗАЦИЯ И НАСТРОЙКА ---
BOT_TOKEN = os.environ.get('BOT_TOKEN', '')
GEMINI_KEY = os.environ.get('GEMINI_API_KEY', '')

bot = telebot.TeleBot(BOT_TOKEN)

# Настройка актуальной модели Gemini
if GEMINI_KEY:
    genai.configure(api_key=GEMINI_KEY)
    ai_model = genai.GenerativeModel('gemini-2.5-flash')
else:
    ai_model = None

# --- 2. БАЗА ДАННЫХ SQLITE ---
def init_db():
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

def save_user(user_id, username, first_name):
    conn = sqlite3.connect('bot_database.db')
    cursor = conn.cursor()
    cursor.execute('''
        INSERT INTO users (user_id, username, first_name, query_count)
        VALUES (?, ?, ?, 0)
        ON CONFLICT(user_id) DO UPDATE SET
            username=excluded.username,
            first_name=excluded.first_name
    ''', (user_id, username, first_name))
    conn.commit()
    conn.close()

def increment_queries(user_id):
    conn = sqlite3.connect('bot_database.db')
    cursor = conn.cursor()
    cursor.execute('UPDATE users SET query_count = query_count + 1 WHERE user_id = ?', (user_id,))
    conn.commit()
    conn.close()

def get_stats():
    conn = sqlite3.connect('bot_database.db')
    cursor = conn.cursor()
    cursor.execute('SELECT COUNT(*), SUM(query_count) FROM users')
    total_users, total_queries = cursor.fetchone()
    conn.close()
    return total_users or 0, total_queries or 0

init_db()

# --- 3. КЛАВИАТУРА ---
def get_main_keyboard():
    markup = types.ReplyKeyboardMarkup(resize_keyboard=True, row_width=2)
    markup.add(
        types.KeyboardButton("🧠 Спросить ИИ"),
        types.KeyboardButton("📊 Статистика БД"),
        types.KeyboardButton("ℹ️ О боте"),
        types.KeyboardButton("⚙️ Помощь")
    )
    return markup

# --- 4. ОБРАБОТЧИКИ КОМАНД И ТЕКСТА ---
@bot.message_handler(commands=['start', 'help'])
def send_welcome(message):
    save_user(message.from_user.id, message.from_user.username, message.from_user.first_name)
    bot.send_message(
        message.chat.id,
        f"Привет, {message.from_user.first_name}! 🚀\n"
        "Я твой личный ассистент с ИИ и Базой Данных.\n"
        "Задай мне любой вопрос в чате!",
        reply_markup=get_main_keyboard()
    )

@bot.message_handler(func=lambda message: message.text == "📊 Статистика БД")
def show_stats(message):
    users_cnt, queries_cnt = get_stats()
    bot.send_message(
        message.chat.id,
        f"📊 **Статистика сервера (SQLite):**\n\n"
        f"👤 Пользователей в БД: **{users_cnt}**\n"
        f"💬 Запросов к ИИ: **{queries_cnt}**",
        parse_mode="Markdown"
    )

@bot.message_handler(func=lambda message: message.text == "ℹ️ О боте")
def about_bot(message):
    bot.send_message(message.chat.id, "🤖 Бот работает 24/7 на Render. Подключены SQLite и Google Gemini AI.")

@bot.message_handler(func=lambda message: message.text == "⚙️ Помощь")
def help_info(message):
    bot.send_message(message.chat.id, "Просто отправьте любой вопрос в чат — нейросеть сразу сгенерирует ответ!")

@bot.message_handler(func=lambda message: True)
def handle_ai_request(message):
    if message.text == "🧠 Спросить ИИ":
        bot.send_message(message.chat.id, "Напишите вопрос прямо в чат! 👇")
        return

    save_user(message.from_user.id, message.from_user.username, message.from_user.first_name)
    
    if not ai_model:
        bot.reply_to(message, "⚠️ Переменная GEMINI_API_KEY не найдена в Render!")
        return

    status_msg = bot.reply_to(message, "🧠 Думаю...")
    
    try:
        response = ai_model.generate_content(message.text)
        increment_queries(message.from_user.id)
        bot.edit_message_text(response.text, chat_id=status_msg.chat.id, message_id=status_msg.message_id)
    except Exception as e:
        bot.edit_message_text(
            f"❌ Ошибка генерации: {e}\n\n"
            "💡 **Проверьте ключ в Render!** Ключ Google Gemini должен начинаться на `AIzaSy...`",
            chat_id=status_msg.chat.id,
            message_id=status_msg.message_id
        )

# --- 5. СЕРВЕР ДЛЯ RENDER ---
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
    print("Бот запущен...")
    bot.infinity_polling()
