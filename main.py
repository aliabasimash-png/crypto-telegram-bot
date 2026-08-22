import asyncio
import os
import requests
from telegram import Update
from telegram.ext import Application, CommandHandler, ContextTypes
BOT_TOKEN = os.getenv("BOT_TOKEN")
CHANNEL_ID = os.getenv("CHANNEL_ID")

# حد هشدار
LIMIT = 4650

def get_calculation():
    url = "https://api.coingecko.com/api/v3/simple/price"

    parameters = {
        "ids": "cardano,zcash",
        "vs_currencies": "usd"
    }

    response = requests.get(url, params=parameters, timeout=20)
    response.raise_for_status()

    data = response.json()

    ada_price = data["cardano"]["usd"]
    zec_price = data["zcash"]["usd"]

    # فرمول: (قیمت ZEC × 1.2) ÷ قیمت ADA
    result = (zec_price * 1.2) / ada_price

    return ada_price, zec_price, result


def normal_message(ada_price, zec_price, result):
    return (
        "📊 گزارش ۵ دقیقه‌ای\n\n"
        f"🔹 ADA: ${ada_price:,.6f}\n"
        f"🔹 ZEC: ${zec_price:,.2f}\n\n"
        "🧮 فرمول: (ZEC × 1.2) ÷ ADA\n"
        f"✅ نتیجه: {result:,.2f}\n"
        f"🎯 حد هشدار: {LIMIT:,}"
    )


def warning_message(ada_price, zec_price, result):
    return (
        "🚨🚨 هشدار مهم! 🚨🚨\n\n"
        f"عدد از {LIMIT:,} بالاتر رفت!\n\n"
        f"ADA: ${ada_price:,.6f}\n"
        f"ZEC: ${zec_price:,.2f}\n\n"
        f"🧮 نتیجه: {result:,.2f}\n\n"
        "⚠️ نسبت ZEC به ADA از حد تعیین‌شده عبور کرده است."
    )


async def check_price(context: ContextTypes.DEFAULT_TYPE):
    try:
        ada_price, zec_price, result = get_calculation()
        chat_id = context.job.chat_id

        # در هر حالت، گزارش عادی ۵ دقیقه‌ای ارسال شود
        await context.bot.send_message(
            chat_id=chat_id,
            text=normal_message(ada_price, zec_price, result),
            disable_notification=False
        )

        # اگر بالاتر از حد بود، ۵ هشدار پشت سر هم بفرست
        if result > LIMIT:
            for number in range(1, 3):
                await context.bot.send_message(
                    chat_id=chat_id,
                    text=(
                        f"🚨 هشدار {number} از ۵ 🚨\n\n"
                        + warning_message(ada_price, zec_price, result)
                    ),
                    disable_notification=False
                )

                # یک ثانیه فاصله بین هشدارها
                await asyncio.sleep(1)

    except Exception as error:
        print("خطا در بررسی قیمت:", error)


async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    chat_id = CHANNEL_ID

    # اگر قبلاً فعال بوده، زمان‌بندی قبلی پاک شود
    old_jobs = context.job_queue.get_jobs_by_name(str(chat_id))
    for job in old_jobs:
        job.schedule_removal()

    # همین حالا یک گزارش ارسال می‌کند
    await check_price(
        type("JobContext", (), {
            "bot": context.bot,
            "job": type("Job", (), {"chat_id": chat_id})()
        })()
    )

    # هر ۵ دقیقه = ۳۰۰ ثانیه
    context.job_queue.run_repeating(
        check_price,
        interval=600,
        first=600,
        chat_id=chat_id,
        name=str(chat_id)
    )

    await update.message.reply_text(
        "✅ ربات فعال شد.\n\n"
        "هر ۵ دقیقه گزارش عادی می‌فرستم.\n"
        f"اگر نتیجه بیشتر از {LIMIT:,} شود، ۵ هشدار پشت‌سرهم می‌فرستم."
    )


async def status(update: Update, context: ContextTypes.DEFAULT_TYPE):
    try:
        ada_price, zec_price, result = get_calculation()

        await context.bot.send_message(
    chat_id=CHANNEL_ID,
    text=normal_message(ada_price, zec_price, result)
)

    except Exception as error:
        await update.message.reply_text(f"❌ خطا:\n{error}")


async def stop(update: Update, context: ContextTypes.DEFAULT_TYPE):
    chat_id = CHANNEL_ID

    jobs = context.job_queue.get_jobs_by_name(str(chat_id))
    for job in jobs:
        job.schedule_removal()

    await update.message.reply_text("⛔ گزارش و هشدارهای خودکار متوقف شد.")


def main():
    app = Application.builder().token(BOT_TOKEN).build()

    app.add_handler(CommandHandler("start", start))
    app.add_handler(CommandHandler("status", status))
    app.add_handler(CommandHandler("stop", stop))

    print("ربات در حال اجرا است...")
    app.run_polling()


main()
