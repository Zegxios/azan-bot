import logging
import requests
from datetime import datetime, time
import pytz
from telegram.ext import Application, CommandHandler, ContextTypes

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
                "فجر (صبح)":  t["Fajr"],
                "ظهر":         t["Dhuhr"],
                "عصر":         t["Asr"],
                "مغرب":        t["Maghrib"],
                "عشاء":        t["Isha"],
            }
    except Exception as e:
        logger.error(f"خطا: {e}")
    return None

def schedule_prayers(app):
    times = get_prayer_times()
    if not times:
        logger.error("نتونست اوقات شرعی رو بگیره")
        return

    icons = {"فجر (صبح)": "🌙", "ظهر": "☀️", "عصر": "🌤", "مغرب": "🌇", "عشاء": "🌃"}

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
        logger.info(f"اذان {name} برای ساعت {t_str} تنظیم شد")

async def reschedule_daily(context: ContextTypes.DEFAULT_TYPE):
    """هر روز ساعت ۱ بامداد اوقات رو دوباره تنظیم میکنه"""
    for job in context.job_queue.jobs():
        if job.name not in ["reschedule"]:
            job.schedule_removal()
    schedule_prayers(context.application)

async def cmd_start(update, context):
    await update.message.reply_text("🕌 سلام! بات اذان قم فعاله.\nهر اذان که برسه خودم خبرت میدم 🤍")

async def cmd_azan(update, context):
    times = get_prayer_times()
    if times:
        msg = f"🕌 *اوقات شرعی قم امروز*\n➖➖➖➖➖➖➖➖\n"
        icons = {"فجر (صبح)": "🌙", "ظهر": "☀️", "عصر": "🌤", "مغرب": "🌇", "عشاء": "🌃"}
        for name, t in times.items():
            msg += f"{icons.get(name,'🕐')} *{name}:*  `{t}`\n"
        await update.message.reply_text(msg, parse_mode="Markdown")
    else:
        await update.message.reply_text("❌ خطا در دریافت اوقات شرعی.")

def main():
    app = Application.builder().token(BOT_TOKEN).build()
    app.add_handler(CommandHandler("start", cmd_start))
    app.add_handler(CommandHandler("azan", cmd_azan))

    # تنظیم اوقات امروز
    schedule_prayers(app)

    # هر روز ساعت ۱ بامداد دوباره تنظیم میکنه برای فردا
    reset_time = time(hour=1, minute=0, second=0, tzinfo=IRAN_TZ)
    app.job_queue.run_daily(reschedule_daily, time=reset_time, name="reschedule")

    logger.info("بات در حال اجراست...")
    app.run_polling()

if __name__ == "__main__":
    main()