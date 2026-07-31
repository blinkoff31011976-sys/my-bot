import os
import threading
from http.server import HTTPServer, BaseHTTPRequestHandler
import telebot
from telebot import types

TOKEN = os.environ.get('BOT_TOKEN', '')
bot = telebot.TeleBot(TOKEN)

# --- 1. КЛАВИАТУРЫ И МЕНЮ ---

# Главное меню под полем ввода
def get_main_keyboard():
    markup = types.ReplyKeyboardMarkup(resize_keyboard=True, row_width=2)
    btn1 = types.KeyboardButton("ℹ️ О боте")
    btn2 = types.KeyboardButton("📊 Статистика")
    btn3 = types.KeyboardButton("🔗 Инлайн-меню")
    btn4 = types.KeyboardButton("⚙️ Настройки")
    markup.add(btn1, btn2, btn3, btn4)
    return markup

# Инлайн-кнопки под сообщением
def get_inline_keyboard():
    markup = types.InlineKeyboardMarkup(row_width=2)
    btn_site = types.InlineKeyboardButton("🌐 GitHub Профиль", url="https://github.com")
    btn_action = types.InlineKeyboardButton("⚡ Быстрое действие", callback_data="fast_action")
    markup.add(btn_site, btn_action)
    return markup


# --- 2. ОБРАБОТЧИКИ КОМАНД И КНОПОК ---

@bot.message_handler(commands=['start', 'help'])
def send_welcome(message):
    bot.send_message(
        message.chat.id,
        "Добро пожаловать! Используйте меню ниже для удобного управления 🚀",
        reply_markup=get_main_keyboard()
    )

# Обработка нажатий кнопок главного меню
@bot.message_handler(func=lambda message: message.text == "ℹ️ О боте")
def about_bot(message):
    bot.send_message(message.chat.id, "Я универсальный Telegram-бот, работающий 24/7 на сервере Render! 🤖")

@bot.message_handler(func=lambda message: message.text == "📊 Статистика")
def stats(message):
    bot.send_message(message.chat.id, "Статистика: Все системы работают штатно! 🟢")

@bot.message_handler(func=lambda message: message.text == "⚙️ Настройки")
def settings(message):
    bot.send_message(message.chat.id, "Раздел настроек готов к расширению ⚙️")

@bot.message_handler(func=lambda message: message.text == "🔗 Инлайн-меню")
def show_inline(message):
    bot.send_message(
        message.chat.id,
        "Пример кнопок прямо под сообщением:",
        reply_markup=get_inline_keyboard()
    )

# Обработка нажатий на инлайн-кнопки (callbacks)
@bot.callback_query_handler(func=lambda call: True)
def callback_inline(call):
    if call.data == "fast_action":
        # Мгновенное всплывающее уведомление
        bot.answer_callback_query(call.id, "Действие выполнено мгновенно! ⚡", show_alert=True)


# --- 3. ОБРАБОТКА МЕДИАФАЙЛОВ ---

@bot.message_handler(content_types=['photo'])
def handle_photo(message):
    file_id = message.photo[-1].file_id
    bot.reply_to(message, f"Отличное фото! 📸\nID: `{file_id}`", parse_mode="Markdown")

@bot.message_handler(content_types=['voice'])
def handle_voice(message):
    bot.reply_to(message, f"Голосовое принято! 🎙️ Длительность: {message.voice.duration} сек.")

@bot.message_handler(content_types=['document'])
def handle_document(message):
    size_kb = round(message.document.file_size / 1024, 2)
    bot.reply_to(message, f"Файл {message.document.file_name} ({size_kb} КБ) принят! 📄")

@bot.message_handler(func=lambda message: True)
def echo_all(message):
    bot.reply_to(message, f"Вы написали: {message.text}")


# --- 4. СЛУЖЕБНЫЙ СЕРВЕР RENDER ---

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
