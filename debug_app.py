from flask import Flask
import threading
import asyncio
import logging
import traceback
import sys

app = Flask(__name__)

@app.route('/')
def home():
    return "Bot ishlayapti! 🤖"

@app.route('/health')
def health():
    return {"status": "ok", "message": "Bot is running"}

async def run_bot():
    """Botni background da ishga tushirish"""
    try:
        logging.basicConfig(level=logging.INFO)
        print("Starting bot initialization...")
        
        # Import bot here to catch errors
        from concursbot import bot, dp, init_db
        
        print("Initializing database...")
        await init_db()
        
        print("Starting bot polling...")
        await dp.start_polling()
        
    except Exception as e:
        print(f"ERROR in bot: {e}")
        print(f"TRACEBACK: {traceback.format_exc()}")
        sys.exit(1)

def start_bot():
    try:
        print("Creating event loop...")
        loop = asyncio.new_event_loop()
        asyncio.set_event_loop(loop)
        print("Running bot...")
        loop.run_until_complete(run_bot())
    except Exception as e:
        print(f"ERROR in start_bot: {e}")
        print(f"TRACEBACK: {traceback.format_exc()}")
        sys.exit(1)

# Botni background thread da ishga tushirish
print("Starting bot thread...")
threading.Thread(target=start_bot, daemon=True).start()

if __name__ == "__main__":
    print("Starting Flask app...")
    app.run(host="0.0.0.0", port=10000)
