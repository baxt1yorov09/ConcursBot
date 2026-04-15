from flask import Flask
import threading
import asyncio
import logging
from concursbot import bot, dp, init_db

app = Flask(__name__)

@app.route('/')
def home():
    return "Bot ishlayapti! 🤖"

@app.route('/health')
def health():
    return {"status": "ok", "message": "Bot is running"}

async def run_bot():
    """Botni background da ishga tushirish"""
    logging.basicConfig(level=logging.INFO)
    await init_db()
    await dp.start_polling()

# Botni background thread da ishga tushirish
def start_bot():
    loop = asyncio.new_event_loop()
    asyncio.set_event_loop(loop)
    loop.run_until_complete(run_bot())

threading.Thread(target=start_bot, daemon=True).start()

if __name__ == "__main__":
    app.run(host="0.0.0.0", port=10000)
