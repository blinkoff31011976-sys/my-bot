import os
import threading
from http.server import HTTPServer, BaseHTTPRequestHandler
import telebot

# Получаем токен из настроек сервера (или используем значение по умолчанию)
TOKEN = os.environ.get('BOT_TOKEN', 'ВАШ_ТОКЕН_БОТА')
bot = telebot.TeleBot(TOKEN)

# Ответ на команду /start и /help
@bot.message_handler(commands=['start', 'help'])
def send_welcome(message):
    bot.reply_to(message, "Привет! Я твой бот, успешно работающий на сервере! 🚀")

# Новый обработчик для фотографий 📸
@bot.message_handler(content_types=['photo'])
def handle_photo(message):
    bot.reply_to(message, "Отличное фото! Я его получил 📸")# Эхо-ответ на любые другие сообщения
@bot.message_handler(func=lambda message: True)
def echo_all(message):
    bot.reply_to(message, message.text)

# Микро-сервер для поддержки работы на Render
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
    # Запускаем веб-проверку в фоновом режиме
    threading.Thread(target=run_http_server, daemon=True).start()
    # Запускаем бота
    print("Бот запущен...")
    bot.infinity_polling()
