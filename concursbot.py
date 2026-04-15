import logging
import aiosqlite
import asyncio
from datetime import datetime, timedelta
from aiogram import Bot, Dispatcher, types
from aiogram.types import InlineKeyboardMarkup, InlineKeyboardButton, ParseMode
from aiogram.utils import executor
from aiogram.utils.exceptions import MessageNotModified


from flask import Flask
import threading

app = Flask(__name__)

@app.route('/')
def home():
    return "Bot ishlayapti"

def run():
    app.run(host="0.0.0.0", port=10000)

threading.Thread(target=run).start()



TOKEN = "8704916545:AAFXQMIiQDy7viSehEDAhF0XlX2_euTFbro"
ADMIN_IDS = [5475526744, 5687217504]

bot = Bot(token=TOKEN)
dp = Dispatcher(bot)

DB = "bot.db"
channel_mode = None  # "add" yoki "remove"

REQUIRED_INVITES = 5
CHANNELS = []
PRIZE_CHANNEL = -1003622119153

BOT_NAME = "🎯 GIFT BOT"

# -------- DB --------
async def init_db():
    async with aiosqlite.connect(DB) as db:
        await db.execute("""
        CREATE TABLE IF NOT EXISTS users(
            user_id INTEGER PRIMARY KEY,
            invited_by INTEGER,
            invites INTEGER DEFAULT 0,
            invited_users TEXT DEFAULT '',
            rewarded INTEGER DEFAULT 0,
            join_date DATETIME DEFAULT CURRENT_TIMESTAMP,
            last_active DATETIME DEFAULT CURRENT_TIMESTAMP,
            is_blocked INTEGER DEFAULT 0,
            suspicious_score INTEGER DEFAULT 0,
            prize_link TEXT DEFAULT '',
            link_used INTEGER DEFAULT 0
        )
        """)
        await db.commit()

        try:
            await db.execute("ALTER TABLE users ADD COLUMN prize_link TEXT DEFAULT ''")
        except:
            pass

        try:
            await db.execute("ALTER TABLE users ADD COLUMN link_used INTEGER DEFAULT 0")
        except:
            pass

        await db.commit()

        await db.execute("""
        CREATE TABLE IF NOT EXISTS anti_cheat_logs(
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            user_id INTEGER,
            action TEXT,
            details TEXT,
            timestamp DATETIME DEFAULT CURRENT_TIMESTAMP
        )
        """)
        await db.commit()

# -------- ADMIN FUNCTIONS --------
def is_admin(user_id):
    return user_id in ADMIN_IDS

# -------- ANTI-CHEAT FUNCTIONS --------
async def log_suspicious_activity(user_id, action, details):
    try:
        async with aiosqlite.connect(DB) as db:
            await db.execute(
                "INSERT INTO anti_cheat_logs (user_id, action, details) VALUES (?, ?, ?)",
                (user_id, action, details)
            )
            await db.execute(
                "UPDATE users SET suspicious_score = suspicious_score + 1 WHERE user_id = ?",
                (user_id,)
            )
            await db.commit()
    except:
        pass

async def is_user_suspicious(user_id):
    try:
        async with aiosqlite.connect(DB) as db:
            cur = await db.execute(
                "SELECT suspicious_score, is_blocked FROM users WHERE user_id = ?",
                (user_id,)
            )
            result = await cur.fetchone()
            if not result:
                return False
            score, blocked = result
            return blocked == 1 or score > 5
    except:
        return False

async def update_user_activity(user_id):
    try:
        async with aiosqlite.connect(DB) as db:
            await db.execute(
                "UPDATE users SET last_active = CURRENT_TIMESTAMP WHERE user_id = ?",
                (user_id,)
            )
            await db.commit()
    except:
        pass

# -------- SUB CHECK --------
async def check_sub(user_id):
    if not CHANNELS:
        return True
    for ch in CHANNELS:
        try:
            member = await bot.get_chat_member(ch, user_id)
            if member.status in ["left", "kicked"]:
                return False
        except:
            return False
    return True

# -------- START --------
@dp.message_handler(commands=['start'])
async def start(msg: types.Message):
    user_id = msg.from_user.id
    args = msg.get_args()
    user_name = msg.from_user.first_name

    await update_user_activity(user_id)

    if await is_user_suspicious(user_id):
        await msg.answer(
            "⚠️ <b>Sizning hisobingiz bloklangan!</b>\n\n"
            "🚫 Botdan foydalanishga ruxsat berilmagan.\n"
            "📞 Admin bilan bog'lanish uchun: /admin",
            parse_mode=ParseMode.HTML
        )
        return

    if not await check_sub(user_id):
        kb = InlineKeyboardMarkup(row_width=1)
        for ch in CHANNELS:
            kb.add(InlineKeyboardButton(f"👉 {ch}", url=f"https://t.me/{ch.replace('@','')}"))
        kb.add(InlineKeyboardButton("🔄 Tekshirish", callback_data="check_sub"))
        await msg.answer(
            "📣 Botdan foydalanish uchun kanallarga obuna bo'ling!",
            reply_markup=kb
        )
        return

    async with aiosqlite.connect(DB) as db:
        cur = await db.execute("SELECT * FROM users WHERE user_id=?", (user_id,))
        user = await cur.fetchone()

        if not user:
            invited_by = int(args) if args and args.isdigit() else None

            if invited_by == user_id:
                await log_suspicious_activity(user_id, "self_invite", f"Tried to invite themselves: {user_id}")
                invited_by = None

            await db.execute(
                "INSERT INTO users (user_id, invited_by) VALUES (?, ?)",
                (user_id, invited_by)
            )

            if invited_by and invited_by != user_id:
                if await is_user_suspicious(invited_by):
                    await log_suspicious_activity(user_id, "suspicious_inviter", f"Invited by suspicious user: {invited_by}")
                else:
                    cur = await db.execute(
                        "SELECT invited_users FROM users WHERE user_id=?",
                        (invited_by,)
                    )
                    row = await cur.fetchone()
                    invited_list = row[0].split(",") if row[0] else []

                    if str(user_id) not in invited_list:
                        invited_list.append(str(user_id))
                        await db.execute(
                            "UPDATE users SET invites=invites+1, invited_users=? WHERE user_id=?",
                            (",".join(invited_list), invited_by)
                        )
                    else:
                        await log_suspicious_activity(invited_by, "duplicate_invite", f"Tried to invite same user: {user_id}")

            await db.commit()

        cur = await db.execute("SELECT invites, rewarded FROM users WHERE user_id=?", (user_id,))
        result = await cur.fetchone()
        invites = result[0]
        rewarded = result[1]

    bot_info = await bot.get_me()
    link = f"https://t.me/{bot_info.username}?start={user_id}"

    progress = min(100, (invites / REQUIRED_INVITES) * 100)
    filled = int(progress / 10)
    empty = 10 - filled
    progress_bar = "🟢" * filled + "⚪" * empty

    if rewarded:
        status = "🎁 Siz sovg'ani oldingiz!"
        status_emoji = "✅"
    elif invites >= REQUIRED_INVITES:
        status = "🎉 Sovg'a olishga tayyorsiz!"
        status_emoji = "🎯"
    else:
        status = f"📈 Yana {REQUIRED_INVITES - invites} ta odam taklif qiling"
        status_emoji = "📊"

    welcome_text = f"""
🎉 <b>Xush kelibsiz, {user_name}!</b>

{BOT_NAME} orqali ajoyib sovg'alarni yuting!

📊 <b>Sizning statistikangiz:</b>
{status_emoji} Takliflar: <b>{invites}/{REQUIRED_INVITES}</b>
📈 Progress: {progress_bar} {progress:.0f}%
🎯 Status: {status}

🔗 <b>Sizning referral linkingiz:</b>
<code>{link}</code>

💡 <b>Qanday ishlashini biling:</b>
1. 🔗 Yuqoridagi linkni do'stlaringizga yuboring
2. 👥 {REQUIRED_INVITES} ta odam taklif qiling
3. 🎁 Ajoyib sovg'alarga ega bo'ling!

🚀 <b>Boshlash uchun tugmalardan foydalaning:</b>
"""

    kb = InlineKeyboardMarkup(row_width=2)
    kb.add(
        InlineKeyboardButton("✅ Tekshirish", callback_data="check"),
        InlineKeyboardButton("📊 Statistika", callback_data="stat"),
        InlineKeyboardButton("🏆 TOP foydalanuvchilar", callback_data="top"),
        InlineKeyboardButton("📚 Yordam", callback_data="help")
    )

    await msg.answer(welcome_text, reply_markup=kb, parse_mode=ParseMode.HTML)

# -------- CHECK SUBSCRIPTION --------
@dp.callback_query_handler(lambda c: c.data == "check_sub")
async def check_subscription(call: types.CallbackQuery):
    user_id = call.from_user.id
    if await check_sub(user_id):
        await call.message.delete()
        await call.message.answer("✅ Siz obuna bo'lgansiz! Endi botdan foydalanishingiz mumkin.")
        await start(call.message)
    else:
        await call.answer("❌ Hali ham obuna emassiz!", show_alert=True)

# -------- CHECK --------
@dp.callback_query_handler(lambda c: c.data == "check")
async def check(call: types.CallbackQuery):
    user_id = call.from_user.id
    user_name = call.from_user.first_name

    await update_user_activity(user_id)

    if await is_user_suspicious(user_id):
        await call.message.edit_text(
            "⚠️ <b>Sizning hisobingiz bloklangan!</b>\n\n"
            "🚫 Botdan foydalanishga ruxsat berilmagan.",
            parse_mode=ParseMode.HTML
        )
        return

    loading_msg = await call.message.answer("🔄 Tekshirilmoqda...")

    try:
        if not await check_sub(user_id):
            await loading_msg.edit_text(
                "❌ <b>Kanallarga obuna bo'ling!</b>\n\n"
                "📡 Majburiy kanallarga obuna bo'lishingiz kerak.\n"
                "🔗 Obuna bo'lgach qaytadan urinib ko'ring.",
                parse_mode=ParseMode.HTML
            )
            return

        async with aiosqlite.connect(DB) as db:
            cur = await db.execute(
                "SELECT invites, rewarded FROM users WHERE user_id=?",
                (user_id,)
            )
            result = await cur.fetchone()
            invites, rewarded = result

            if invites >= REQUIRED_INVITES and rewarded == 0:
                cur = await db.execute("SELECT prize_link, link_used FROM users WHERE user_id=?", (user_id,))
                prize_data = await cur.fetchone()
                prize_link = prize_data[0] if prize_data else None
                link_used = prize_data[1] if prize_data else 0

                if not prize_link:
                    link = await bot.create_chat_invite_link(
                        chat_id=PRIZE_CHANNEL,
                        member_limit=1
                    )
                    prize_link = link.invite_link
                    link_used = 0

                    await db.execute("""
                        UPDATE users 
                        SET rewarded=1, prize_link=?, link_used=? 
                        WHERE user_id=?
                    """, (prize_link, link_used, user_id))
                    await db.commit()

                if link_used == 0:
                    await loading_msg.edit_text(
                        f"🎉 <b>Tabriklaymiz, {user_name}!</b>\n\n"
                        f"🎁 Siz sovg'ani yutdingiz!\n"
                        f"🔗 Quyidagi maxsus linkingiz (FAQAT 1 MARTA ISHLAYDI):\n\n"
                        f"<code>{prize_link}</code>\n\n"
                        f"⚠️ <b>MUHIM:</b>\n"
                        f"• Link faqat 1 marta ishlaydi\n"
                        f"• Kirgandan so'ng avtomatik o'chadi\n"
                        f"• 2-marta urinib bo'lmaydi\n\n"
                        f"✅ <b>Hozir kirish uchun yuqoridagi linkni bosing!</b>",
                        parse_mode=ParseMode.HTML
                    )
                else:
                    await loading_msg.edit_text(
                        f"⚠️ <b>Link allaqachon ishlatilgan, {user_name}!</b>\n\n"
                        f"🚫 Sizning sovg'angiz uchun link allaqachon ishlatilgan.\n\n"
                        f"📞 Muammo bo'lsa admin bilan bog'laning: /admin",
                        parse_mode=ParseMode.HTML
                    )

            elif rewarded == 1:
                cur = await db.execute("SELECT prize_link, link_used FROM users WHERE user_id=?", (user_id,))
                prize_data = await cur.fetchone()
                prize_link = prize_data[0] if prize_data else None
                link_used = prize_data[1] if prize_data else 0

                if prize_link and link_used == 0:
                    await loading_msg.edit_text(
                        f"🎉 <b>Sizda link mavjud, {user_name}!</b>\n\n"
                        f"🎁 Sizning sovg'angiz uchun link:\n\n"
                        f"<code>{prize_link}</code>\n\n"
                        f"⚠️ Link faqat bir marta ishlaydi!",
                        parse_mode=ParseMode.HTML
                    )
                else:
                    await loading_msg.edit_text(
                        f"🎁 <b>Siz allaqachon sovg'ani olgansiz, {user_name}!</b>\n\n"
                        "Prize kanalga kirishingiz mumkin bo'lgan linkni allaqachon oldingiz.",
                        parse_mode=ParseMode.HTML
                    )

            else:
                needed = REQUIRED_INVITES - invites
                await loading_msg.edit_text(
                    f"📊 <b>Hali tayyor emas, {user_name}!</b>\n\n"
                    f"👥 Sizda: <b>{invites}/{REQUIRED_INVITES}</b> ta taklif\n"
                    f"📈 Yana: <b>{needed}</b> ta odam taklif qilishingiz kerak\n\n"
                    f"💡 Do'stlaringizga referral linkingizni yuboring!",
                    parse_mode=ParseMode.HTML
                )
    except Exception as e:
        import traceback
        traceback.print_exc()
        await log_suspicious_activity(user_id, "check_error", str(e))

        error_msg = "❌ <b>Xatolik yuz berdi!</b>\n\n🔄 Iltimos, qaytadan urinib ko'ring."
        if is_admin(user_id):
            error_msg = f"🐛 <b>DEBUG:</b> {type(e).__name__}: {str(e)}\n\n❌ <b>Xatolik yuz berdi!</b>"

        await loading_msg.edit_text(error_msg, parse_mode=ParseMode.HTML)

# -------- STAT --------
@dp.callback_query_handler(lambda c: c.data == "stat")
async def stat(call: types.CallbackQuery):
    user_id = call.from_user.id
    user_name = call.from_user.first_name

    if not await check_sub(user_id):
        return

    async with aiosqlite.connect(DB) as db:
        cur = await db.execute(
            "SELECT invites, rewarded FROM users WHERE user_id=?",
            (user_id,)
        )
        result = await cur.fetchone()
        invites = result[0]
        rewarded = result[1]

        cur = await db.execute(
            "SELECT COUNT(*) + 1 FROM users WHERE invites > ?",
            (invites,)
        )
        rank = (await cur.fetchone())[0]

    progress = min(100, (invites / REQUIRED_INVITES) * 100)
    filled = int(progress / 10)
    empty = 10 - filled
    progress_bar = "🟢" * filled + "⚪" * empty

    status = "🎁 Sovg'a olgan" if rewarded else "🎯 Faol ishtirokchi"

    stat_text = f"""
📊 <b>{user_name} - Statistika</b>

🏆 Reyting: <b>#{rank}</b>
👥 Takliflar: <b>{invites}/{REQUIRED_INVITES}</b>
📈 Progress: {progress_bar} {progress:.0f}%
🎯 Status: {status}

💡 <b>Qisqacha ma'lumot:</b>
• Har bir do'stingiz sizga 1 ball beradi
• {REQUIRED_INVITES} ta taklif = sovg'a
• Eng yaxshi 10 o'yinchi TOP da ko'rinadi
    """

    kb = InlineKeyboardMarkup()
    kb.add(InlineKeyboardButton("🔙 Orqaga", callback_data="back_to_main"))

    try:
        await call.message.edit_text(stat_text, reply_markup=kb, parse_mode=ParseMode.HTML)
    except MessageNotModified:
        pass

# -------- TOP --------
@dp.callback_query_handler(lambda c: c.data == "top")
async def top(call: types.CallbackQuery):
    async with aiosqlite.connect(DB) as db:
        cur = await db.execute(
            "SELECT user_id, invites FROM users ORDER BY invites DESC LIMIT 10"
        )
        rows = await cur.fetchall()

        cur = await db.execute(
            "SELECT invites FROM users WHERE user_id=?",
            (call.from_user.id,)
        )
        user_invites = (await cur.fetchone())[0]

        cur = await db.execute(
            "SELECT COUNT(*) + 1 FROM users WHERE invites > ?",
            (user_invites,)
        )
        user_rank = (await cur.fetchone())[0]

    text = "🏆 <b>TOP 10 Foydalanuvchilar</b>\n\n"
    medals = ["🥇", "🥈", "🥉"]

    for i, (user_id, invites) in enumerate(rows, 1):
        medal = medals[i-1] if i <= 3 else f"{i}."
        text += f"{medal} <code>{user_id}</code> — <b>{invites}</b> ta\n"

    text += f"\n📍 <b>Sizning reytingingiz:</b> #{user_rank} ({user_invites} ta)"

    kb = InlineKeyboardMarkup()
    kb.add(InlineKeyboardButton("🔄 Yangilash", callback_data="top"))
    kb.add(InlineKeyboardButton("🔙 Orqaga", callback_data="back_to_main"))

    try:
        await call.message.edit_text(text, reply_markup=kb, parse_mode=ParseMode.HTML)
    except MessageNotModified:
        pass

# -------- HELP --------
@dp.callback_query_handler(lambda c: c.data == "help")
async def help_callback(call: types.CallbackQuery):
    help_text = f"""
📚 <b>{BOT_NAME} - Yordam</b>

💡 <b>Bot qanday ishlaydi?</b>

1️⃣ <b>Ro'yxatdan o'tish:</b>
   • /start buyrug'ini yuboring
   • Sizga shaxsiy referral link beriladi

2️⃣ <b>Taklif qilish:</b>
   • Linkni do'stlaringizga yuboring
   • Har bir yangi foydalanuvchi = 1 ball

3️⃣ <b>Sovg'a olish:</b>
   • {REQUIRED_INVITES} ta odam taklif qiling
   • Prize kanalga bepul kirish

🎯 <b>Qoidalari:</b>
• Faqat haqiqiy foydalanuvchilar hisoblanadi
• O'zingizni o'zingiz taklif qila olmaysiz
• Bir kishi bir marta hisoblanadi

🏆 <b>Qo'shimcha imkoniyatlar:</b>
• TOP 10 o'yinchi ro'yxati
• Batafsil statistika

❓ <b>Qo'shimcha savollar uchun admin ga murojaat qiling!</b>
    """

    kb = InlineKeyboardMarkup()
    kb.add(InlineKeyboardButton("🔙 Orqaga", callback_data="back_to_main"))

    try:
        await call.message.edit_text(help_text, reply_markup=kb, parse_mode=ParseMode.HTML)
    except MessageNotModified:
        pass

@dp.callback_query_handler(lambda c: c.data == "back_to_main")
async def back_to_main(call: types.CallbackQuery):
    await start(call.message)

# ================= ADMIN =================
def admin_kb():
    kb = InlineKeyboardMarkup(row_width=2)
    kb.add(
        InlineKeyboardButton("📢 Broadcast", callback_data="broadcast"),
        InlineKeyboardButton("📊 Statistika", callback_data="admin_stat")
    )
    kb.add(
        InlineKeyboardButton("⚙️ Invite soni", callback_data="set_inv"),
        InlineKeyboardButton("🎁 Prize kanal", callback_data="set_prize")
    )
    kb.add(
        InlineKeyboardButton("📡 Majburiy kanallar", callback_data="set_channels"),
        InlineKeyboardButton("👥 Foydalanuvchilar", callback_data="users_list")
    )
    kb.add(
        InlineKeyboardButton("🚫 Anti-cheat", callback_data="anti_cheat"),
        InlineKeyboardButton("🔙 Orqaga", callback_data="back_to_main")
    )
    return kb

def admin_text():
    return f"""
🛠️ <b>Admin Panel - {BOT_NAME}</b>

👋 Xush kelibsiz, Admin!

📊 <b>Boshqaruv imkoniyatlari:</b>
• 📢 Barcha foydalanuvchilarga xabar yuborish
• ⚙️ Takliflar sonini o'zgartirish
• 🎁 Prize kanalni sozlash
• 📡 Majburiy kanallarni boshqarish
• 👥 Foydalanuvchilar ro'yxati

🎯 <b>Joriy sozlamalar:</b>
• Takliflar soni: <b>{REQUIRED_INVITES}</b>
• Prize kanal: <code>{PRIZE_CHANNEL}</code>
• Majburiy kanallar: <b>{len(CHANNELS)}</b> ta
        """

@dp.message_handler(commands=['admin'])
async def admin(msg: types.Message):
    user_id = msg.from_user.id
    await update_user_activity(user_id)

    if await is_user_suspicious(user_id):
        await msg.answer(
            "⚠️ <b>Sizning hisobingiz bloklangan!</b>\n\n"
            "🚫 Botdan foydalanishga ruxsat berilmagan.",
            parse_mode=ParseMode.HTML
        )
        return

    if is_admin(user_id):
        await msg.answer(admin_text(), reply_markup=admin_kb(), parse_mode=ParseMode.HTML)

# -------- BROADCAST --------
broadcast_mode = False

@dp.callback_query_handler(lambda c: c.data == "broadcast")
async def broadcast_start(call: types.CallbackQuery):
    global broadcast_mode
    if not is_admin(call.from_user.id):
        return
    broadcast_mode = True
    await call.message.answer(
        "📢 <b>Broadcast rejimi</b>\n\n"
        "✍️ Yubormoqchi bo'lgan xabaringizni yozing:\n\n"
        "⚠️ Eslatma: Xabar barcha foydalanuvchilarga yuboriladi!",
        parse_mode=ParseMode.HTML
    )

# -------- ADMIN STAT --------
@dp.callback_query_handler(lambda c: c.data == "admin_stat")
async def admin_stat(call: types.CallbackQuery):
    if not is_admin(call.from_user.id):
        return

    async with aiosqlite.connect(DB) as db:
        cur = await db.execute("SELECT COUNT(*) FROM users")
        total_users = (await cur.fetchone())[0]

        cur = await db.execute("SELECT COUNT(*) FROM users WHERE invites > 0")
        active_users = (await cur.fetchone())[0]

        cur = await db.execute("SELECT COUNT(*) FROM users WHERE rewarded = 1")
        rewarded_users = (await cur.fetchone())[0]

        cur = await db.execute("SELECT SUM(invites) FROM users")
        total_invites = (await cur.fetchone())[0] or 0

    stat_text = f"""
📊 <b>Bot Statistikasi</b>

👥 <b>Foydalanuvchilar:</b>
• Jami: <b>{total_users}</b> ta
• Faol: <b>{active_users}</b> ta
• Sovg'a olgan: <b>{rewarded_users}</b> ta

🎯 <b>Takliflar:</b>
• Jami: <b>{total_invites}</b> ta
• O'rtacha: <b>{total_invites / max(total_users, 1):.1f}</b> ta/user

📈 <b>Statistika:</b>
• Faollik: <b>{(active_users / max(total_users, 1) * 100):.1f}%</b>
• Konversiya: <b>{(rewarded_users / max(total_users, 1) * 100):.1f}%</b>

⚙️ <b>Joriy sozlamalar:</b>
• Required invites: <b>{REQUIRED_INVITES}</b>
• Prize channel: <code>{PRIZE_CHANNEL}</code>
    """

    kb = InlineKeyboardMarkup()
    kb.add(InlineKeyboardButton("🔄 Yangilash", callback_data="admin_stat"))
    kb.add(InlineKeyboardButton("🔙 Orqaga", callback_data="admin_back"))

    try:
        await call.message.edit_text(stat_text, reply_markup=kb, parse_mode=ParseMode.HTML)
    except MessageNotModified:
        pass

# -------- SET INVITES --------
@dp.callback_query_handler(lambda c: c.data == "set_inv")
async def set_inv(call: types.CallbackQuery):
    if not is_admin(call.from_user.id):
        return
    await call.message.answer(
        f"⚙️ <b>Takliflar sonini o'zgartirish</b>\n\n"
        f"📊 Joriy qiymat: <b>{REQUIRED_INVITES}</b>\n\n"
        "✍️ Yangi sonni kiriting (masalan: 5, 10, 15):",
        parse_mode=ParseMode.HTML
    )

# -------- SET PRIZE --------
@dp.callback_query_handler(lambda c: c.data == "set_prize")
async def set_prize(call: types.CallbackQuery):
    if not is_admin(call.from_user.id):
        return
    await call.message.answer(
        f"🎁 <b>Prize kanalni o'zgartirish</b>\n\n"
        f"📊 Joriy kanal: <code>{PRIZE_CHANNEL}</code>\n\n"
        "✍️ Yangi kanal @username ni kiriting:",
        parse_mode=ParseMode.HTML
    )

# -------- SET CHANNELS --------
@dp.callback_query_handler(lambda c: c.data == "set_channels")
async def set_channels(call: types.CallbackQuery):
    if not is_admin(call.from_user.id):
        return
    current_channels = ", ".join(CHANNELS) if CHANNELS else "Yo'q"

    kb = InlineKeyboardMarkup(row_width=2)
    kb.add(
        InlineKeyboardButton("➕ Kanal qo'shish", callback_data="channel_add"),
        InlineKeyboardButton("➖ Kanal o'chirish", callback_data="channel_remove")
    )
    kb.add(
        InlineKeyboardButton("📋 Kanallar ro'yxati", callback_data="channel_list"),
        InlineKeyboardButton("🔄 Barchasini almashtirish", callback_data="channel_replace")
    )
    kb.add(InlineKeyboardButton("🔙 Orqaga", callback_data="admin_back"))

    await call.message.edit_text(
        f"📡 <b>Majburiy kanallarni boshqarish</b>\n\n"
        f"📊 Joriy kanallar ({len(CHANNELS)} ta): <code>{current_channels}</code>\n\n"
        "🔽 Kerakli amalni tanlang:",
        reply_markup=kb,
        parse_mode=ParseMode.HTML
    )

# -------- CHANNEL ADD --------
@dp.callback_query_handler(lambda c: c.data == "channel_add")
async def channel_add(call: types.CallbackQuery):
    global channel_mode
    if not is_admin(call.from_user.id):
        return
    channel_mode = "add"
    await call.message.answer(
        "➕ <b>Kanal qo'shish rejimi</b>\n\n"
        "✍️ Kanal @username ni kiriting:\n"
        "Masalan: @mychannel",
        parse_mode=ParseMode.HTML
    )

# -------- CHANNEL REMOVE --------
@dp.callback_query_handler(lambda c: c.data == "channel_remove")
async def channel_remove(call: types.CallbackQuery):
    global channel_mode
    if not is_admin(call.from_user.id):
        return
    channel_mode = "remove"
    await call.message.answer(
        "➖ <b>Kanal o'chirish rejimi</b>\n\n"
        f"📋 Mavjud kanallar: {', '.join(CHANNELS) if CHANNELS else 'Yoq'}\n\n"
        "✍️ O'chiriladigan kanal @username ni kiriting:",
        parse_mode=ParseMode.HTML
    )

# -------- CHANNEL LIST --------
@dp.callback_query_handler(lambda c: c.data == "channel_list")
async def channel_list(call: types.CallbackQuery):
    if not CHANNELS:
        channels_text = "📋 <b>Majburiy kanallar yo'q</b>\n\n⚪ Hozircha hech qanday kanal majburiy emas."
    else:
        channels_text = "📋 <b>Majburiy kanallar ro'yxati</b>\n\n"
        for i, channel in enumerate(CHANNELS, 1):
            channels_text += f"{i}. <code>{channel}</code>\n"
        channels_text += f"\n📊 Jami: <b>{len(CHANNELS)}</b> ta kanal"

    kb = InlineKeyboardMarkup()
    kb.add(InlineKeyboardButton("🔙 Orqaga", callback_data="set_channels"))

    await call.message.edit_text(channels_text, reply_markup=kb, parse_mode=ParseMode.HTML)

# -------- CHANNEL REPLACE --------
@dp.callback_query_handler(lambda c: c.data == "channel_replace")
async def channel_replace(call: types.CallbackQuery):
    if not is_admin(call.from_user.id):
        return
    await call.message.edit_text(
        "🔄 <b>Barcha kanallarni almashtirish</b>\n\n"
        "✍️ Yangi kanallarni vergul bilan kiriting:\n"
        "Masalan: @channel1,@channel2,@channel3\n\n"
        "📊 Joriy kanallar: " + (', '.join(CHANNELS) if CHANNELS else "Yo'q"),
        parse_mode=ParseMode.HTML
    )

# -------- USERS LIST --------
@dp.callback_query_handler(lambda c: c.data == "users_list")
async def users_list(call: types.CallbackQuery):
    if not is_admin(call.from_user.id):
        return

    async with aiosqlite.connect(DB) as db:
        cur = await db.execute(
            "SELECT user_id, invites, rewarded FROM users ORDER BY user_id DESC LIMIT 20"
        )
        users = await cur.fetchall()

    text = "👥 <b>Oxirgi 20 foydalanuvchi</b>\n\n"

    for user_id, invites, rewarded in users:
        status = "🎁" if rewarded else "🎯" if invites > 0 else "👤"
        text += f"{status} <code>{user_id}</code> — <b>{invites}</b> ta\n"

    kb = InlineKeyboardMarkup()
    kb.add(InlineKeyboardButton("🔄 Yangilash", callback_data="users_list"))
    kb.add(InlineKeyboardButton("🔙 Orqaga", callback_data="admin_back"))

    try:
        await call.message.edit_text(text, reply_markup=kb, parse_mode=ParseMode.HTML)
    except MessageNotModified:
        pass

# -------- ANTI-CHEAT --------
@dp.callback_query_handler(lambda c: c.data == "anti_cheat")
async def anti_cheat_panel(call: types.CallbackQuery):
    if not is_admin(call.from_user.id):
        return

    try:
        async with aiosqlite.connect(DB) as db:
            cur = await db.execute(
                "SELECT user_id, suspicious_score, is_blocked FROM users WHERE suspicious_score > 0 ORDER BY suspicious_score DESC LIMIT 10"
            )
            suspicious_users = await cur.fetchall()

            cur = await db.execute(
                "SELECT user_id, action, details, timestamp FROM anti_cheat_logs ORDER BY timestamp DESC LIMIT 10"
            )
            logs = await cur.fetchall()
    except:
        suspicious_users = []
        logs = []

    text = "🚫 <b>Anti-Cheat Panel</b>\n\n"

    if suspicious_users:
        text += "🔍 <b>Shubhali foydalanuvchilar:</b>\n\n"
        for user_id, score, blocked in suspicious_users:
            status = "🚫 Bloklangan" if blocked else f"⚠️ Ball: {score}"
            text += f"• <code>{user_id}</code> — {status}\n"
    else:
        text += "✅ Shubhaliliklar yo'q\n\n"

    text += "\n📋 <b>So'nggi loglar:</b>\n\n"
    for user_id, action, details, timestamp in logs:
        text += f"• {timestamp[:19]} — <code>{user_id}</code> — {action}\n"

    kb = InlineKeyboardMarkup()
    kb.add(InlineKeyboardButton("🔄 Yangilash", callback_data="anti_cheat"))
    kb.add(InlineKeyboardButton("🔙 Orqaga", callback_data="admin_back"))

    try:
        await call.message.edit_text(text, reply_markup=kb, parse_mode=ParseMode.HTML)
    except MessageNotModified:
        pass

# -------- ADMIN BACK --------
@dp.callback_query_handler(lambda c: c.data == "admin_back")
async def admin_back(call: types.CallbackQuery):
    if not is_admin(call.from_user.id):
        return
    try:
        await call.message.edit_text(admin_text(), reply_markup=admin_kb(), parse_mode=ParseMode.HTML)
    except MessageNotModified:
        pass

# -------- ADD ADMIN --------
@dp.message_handler(commands=['add_admin'])
async def add_admin(msg: types.Message):
    if is_admin(msg.from_user.id):
        args = msg.get_args().split()
        if len(args) != 1 or not args[0].isdigit():
            await msg.answer("Ishlatish: /add_admin &lt;user_id&gt;", parse_mode=ParseMode.HTML)
            return
        new_admin_id = int(args[0])
        if new_admin_id in ADMIN_IDS:
            await msg.answer(f"✅ User {new_admin_id} allaqachon admin!")
        else:
            ADMIN_IDS.append(new_admin_id)
            await msg.answer(f"✅ User {new_admin_id} admin qilindi!")

# -------- REMOVE ADMIN --------
@dp.message_handler(commands=['remove_admin'])
async def remove_admin(msg: types.Message):
    if msg.from_user.id == ADMIN_IDS[0]:
        args = msg.get_args().split()
        if len(args) != 1 or not args[0].isdigit():
            await msg.answer("Ishlatish: /remove_admin &lt;user_id&gt;", parse_mode=ParseMode.HTML)
            return
        remove_admin_id = int(args[0])
        if remove_admin_id == ADMIN_IDS[0]:
            await msg.answer("❌ Asosiy adminni o'chirib bo'lmaydi!")
        elif remove_admin_id in ADMIN_IDS:
            ADMIN_IDS.remove(remove_admin_id)
            await msg.answer(f"✅ User {remove_admin_id} admin ro'yxatidan o'chirildi!")
        else:
            await msg.answer(f"⚠️ User {remove_admin_id} admin emas!")

# -------- LIST ADMINS --------
@dp.message_handler(commands=['list_admins'])
async def list_admins(msg: types.Message):
    if is_admin(msg.from_user.id):
        admin_list = "\n".join([f"   <code>{aid}</code>" for aid in ADMIN_IDS])
        await msg.answer(f"<b>Adminlar ro'yxati:</b>\n{admin_list}", parse_mode=ParseMode.HTML)

# -------- PRIZE CHANNEL JOIN TRACKING --------
@dp.message_handler(content_types=['new_chat_members'])
async def track_prize_join(msg: types.Message):
    if msg.chat.username and msg.chat.username.lstrip('@') == str(PRIZE_CHANNEL).lstrip('@'):
        for new_member in msg.new_chat_members:
            user_id = new_member.id
            async with aiosqlite.connect(DB) as db:
                await db.execute(
                    "UPDATE users SET link_used=1 WHERE user_id=?",
                    (user_id,)
                )
                await db.commit()
            await log_suspicious_activity(user_id, "prize_joined", "User joined prize channel via link")

# ================================================================
# UNIFIED TEXT MESSAGE HANDLER — barcha to'qnashuvlar hal qilindi
# ================================================================
@dp.message_handler(content_types=['text'])
async def handle_text(msg: types.Message):
    global CHANNELS, PRIZE_CHANNEL, REQUIRED_INVITES, channel_mode, broadcast_mode

    if not is_admin(msg.from_user.id):
        return

    text = msg.text.strip()

    # 1. BROADCAST rejimi
    if broadcast_mode:
        broadcast_mode = False
        loading_msg = await msg.answer("🔄 Yuborilmoqda...")

        async with aiosqlite.connect(DB) as db:
            cur = await db.execute("SELECT user_id FROM users")
            users = await cur.fetchall()

        sent = 0
        failed = 0
        for u in users:
            try:
                await bot.send_message(
                    u[0],
                    f"📢 <b>Admin xabari:</b>\n\n{text}",
                    parse_mode=ParseMode.HTML
                )
                sent += 1
                await asyncio.sleep(0.1)
            except:
                failed += 1

        await loading_msg.edit_text(
            f"✅ <b>Broadcast tugadi!</b>\n\n"
            f"👥 Yuborildi: <b>{sent}</b> ta\n"
            f"❌ Xatolik: <b>{failed}</b> ta\n"
            f"📊 Jami: <b>{len(users)}</b> ta",
            parse_mode=ParseMode.HTML
        )
        return

    # 2. KANAL QO'SHISH rejimi
    if channel_mode == "add":
        if not text.startswith("@"):
            await msg.answer("⚠️ Kanal @username bilan boshlanishi kerak!\nMasalan: @mychannel")
            return
        if text in CHANNELS:
            await msg.answer(
                f"⚠️ <b>{text}</b> allaqachon mavjud!",
                parse_mode=ParseMode.HTML
            )
        else:
            CHANNELS.append(text)
            await msg.answer(
                f"✅ <b>Kanal qo'shildi!</b>\n\n"
                f"📡 Yangi kanal: <code>{text}</code>\n"
                f"📊 Jami kanallar: <b>{len(CHANNELS)}</b> ta\n\n"
                f"📋 Barcha kanallar: {', '.join(CHANNELS)}",
                parse_mode=ParseMode.HTML
            )
        channel_mode = None
        return

    # 3. KANAL O'CHIRISH rejimi
    if channel_mode == "remove":
        if not text.startswith("@"):
            await msg.answer("⚠️ Kanal @username bilan boshlanishi kerak!")
            return
        if text in CHANNELS:
            CHANNELS.remove(text)
            await msg.answer(
                f"✅ <b>Kanal o'chirildi!</b>\n\n"
                f"📡 O'chirilgan: <code>{text}</code>\n"
                f"📊 Qolgan kanallar: <b>{len(CHANNELS)}</b> ta\n"
                f"📋 Qolganlar: {', '.join(CHANNELS) if CHANNELS else 'Yoq'}",
                parse_mode=ParseMode.HTML
            )
        else:
            await msg.answer(
                f"⚠️ <b>Kanal topilmadi!</b>\n\n"
                f"📋 Mavjud kanallar: {', '.join(CHANNELS) if CHANNELS else 'Yoq'}",
                parse_mode=ParseMode.HTML
            )
        channel_mode = None
        return

    # 4. KANALLARNI ALMASHTIRISH (vergul bilan yozilgan @channel1,@channel2)
    if "," in text and all(part.strip().startswith("@") for part in text.split(",")):
        old_channels = CHANNELS.copy()
        CHANNELS = [ch.strip() for ch in text.split(",") if ch.strip()]
        await msg.answer(
            f"✅ <b>Majburiy kanallar yangilandi!</b>\n\n"
            f"📊 Oldin: <b>{len(old_channels)}</b> ta\n"
            f"📊 Yangi: <b>{len(CHANNELS)}</b> ta\n\n"
            f"📡 Yangi kanallar: {', '.join(CHANNELS)}",
            parse_mode=ParseMode.HTML
        )
        return

    # 5. PRIZE KANAL o'zgartirish (@username)
    if text.startswith("@"):
        old_channel = PRIZE_CHANNEL
        PRIZE_CHANNEL = text
        await msg.answer(
            f"✅ <b>Prize kanal o'zgartirildi!</b>\n\n"
            f"📊 Oldin: <code>{old_channel}</code>\n"
            f"📊 Yangi: <code>{PRIZE_CHANNEL}</code>",
            parse_mode=ParseMode.HTML
        )
        return

    # 6. INVITE SONI o'zgartirish (faqat raqam, max 3 xona)
    if text.isdigit() and len(text) <= 3:
        old_value = REQUIRED_INVITES
        REQUIRED_INVITES = int(text)
        await msg.answer(
            f"✅ <b>Takliflar soni o'zgartirildi!</b>\n\n"
            f"📊 Oldin: <b>{old_value}</b>\n"
            f"📊 Yangi: <b>{REQUIRED_INVITES}</b>",
            parse_mode=ParseMode.HTML
        )
        return

# -------- MAIN --------
if __name__ == "__main__":
    logging.basicConfig(level=logging.INFO)
    loop = asyncio.get_event_loop()
    loop.run_until_complete(init_db())
    executor.start_polling(dp)

