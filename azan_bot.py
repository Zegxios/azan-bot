import logging
import requests
from datetime import datetime, time
import pytz
from telegram import ReplyKeyboardMarkup, KeyboardButton
from telegram.ext import Application, CommandHandler, MessageHandler, filters, ContextTypes

BOT_TOKEN = "8988319813:AAG95hk2Bi3i6FZTmPLojZRsTNRublLPZZM"
CHAT_ID = "200322275"

IRAN_TZ = pytz.timezone("Asia/Tehran")

logging.basicConfig(format="%(asctime)s - %(levelname)s - %(message)s", level=logging.INFO)
logger = logging.getLogger(__name__)

def get_prayer_times():
    try:
        today = datetime.now(IRAN_TZ)
        url = "https://api.aladhan.com/v1/timingsByCity"
        params = {"city": "Qom", "country": "Iran", "method": 7, "date": today.strftime("%d-%m-%Y")}
        response = requests.get(url, params=params, timeout=10)
        data = response.json()
        if data.get("code") == 200:
            t = data["data"]["timings"]
            return {
                "فجر (صبح)": t["Fajr"],
                "طلوع آفتاب": t["Sunrise"],
                "ظهر": t["Dhuhr"],
                "عصر": t["Asr"],
                "مغرب": t["Maghrib"],
                "عشاء": t["Isha"],
            }
    except Exception as e:
        logger.error(f"خطا: {e}")
    return None

def format_message(times):
    today = datetime.now(IRAN_TZ)
    msg = f"🕌 *اوقات شرعی قم*\n📅 {today.strftime('%Y/%m/%d')}\n➖➖➖➖➖➖➖➖\n"
    icons = {"فجر (صبح)": "🌙", "طلوع آفتاب": "🌅", "ظهر": "☀️", "عصر": "🌤", "مغرب": "🌇", "عشاء": "🌃"}
    for name, t in times.items():
        msg += f"{icons.get(name,'🕐')} *{name}:*  `{t}`\n"
    return msg

def main_keyboard():
    keyboard = [
        [KeyboardButton("🕌 اوقات شرعی امروز")],
    ]
    return ReplyKeyboardMarkup(keyboard, resize_keyboard=True)

async def cmd_start(update, context):
    await update.message.reply_text(
        "بسم الله الرحمن الرحیم 🤍\n\n"
        "سلام! به بات اوقات شرعی قم خوش اومدی.\n\n"
        "🕌 هر روز سر اذان بهت پیام میدم.\n"
        "📋 برای دیدن اوقات شرعی امروز دکمه زیر رو بزن 👇",
        reply_markup=main_keyboard()
    )

async def cmd_azan(update, context):
    times = get_prayer_times()
    if times:
        await update.message.reply_text(format_message(times), parse_mode="Markdown")
    else:
        await update.message.reply_text("❌ خطا در دریافت اوقات شرعی.")

async def handle_buttons(update, context):
    text = update.message.text
    if text == "🕌 اوقات شرعی امروز":
        await cmd_azan(update, context)

async def send_daily(context):
    times = get_prayer_times()
    if times:
        await context.bot.send_message(chat_id=CHAT_ID, text=format_message(times), parse_mode="Markdown")

def schedule_prayers(app):
    times = get_prayer_times()
    if not times:
        return
    icons = {"فجر (صبح)": "🌙", "طلوع آفتاب": "🌅", "ظهر": "☀️", "عصر": "🌤", "مغرب": "🌇", "عشاء": "🌃"}
    for name, t_str in times.items():
        hour, minute = map(int, t_str.split(":"))
        send_time = time(hour=hour, minute=minute, second=0, tzinfo=IRAN_TZ)
        icon = icons.get(name, "🕐")
        msg = f"{icon} وقت اذان *{name}* رسید\n🕐 ساعت: `{t_str}`\n🕌 _قم_"
        app.job_queue.run_daily(
            lambda ctx, m=msg: ctx.bot.send_message(chat_id=CHAT_ID, text=m, parse_mode="Markdown"),
            time=send_time,
            name=name
        )

async def reschedule_daily(context):
    for job in context.job_queue.jobs():
        if job.name not in ["reschedule"]:
            job.schedule_removal()
    schedule_prayers(context.application)

def main():
    app = Application.builder().token(BOT_TOKEN).build()
    app.add_handler(CommandHandler("start", cmd_start))
    app.add_handler(CommandHandler("azan", cmd_azan))
    app.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, handle_buttons))

    schedule_prayers(app)
    reset_time = time(hour=1, minute=0, second=0, tzinfo=IRAN_TZ)
    app.job_queue.run_daily(reschedule_daily, time=reset_time, name="reschedule")

    logger.info("بات در حال اجراست...")
    app.run_polling()

if __name__ == "__main__":
    main()
