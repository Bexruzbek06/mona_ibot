import os
import logging
import asyncio

from aiogram import Bot, Dispatcher, F
from aiogram.types import Message
from aiogram.filters import CommandStart
from anthropic import Anthropic

# ============================================================
# SOZLAMALAR — bu ikki qatorga o'z ma'lumotlaringizni kiriting
# ============================================================
TELEGRAM_BOT_TOKEN = os.getenv("TELEGRAM_BOT_TOKEN", "BU_YERGA_TELEGRAM_TOKEN")
ANTHROPIC_API_KEY = os.getenv("ANTHROPIC_API_KEY", "BU_YERGA_ANTHROPIC_API_KEY")

# Botning "shaxsiyati" — kerak bo'lsa o'zgartiring
SYSTEM_PROMPT = (
    "Sen mona_ibot nomli Telegram botisan. Foydalanuvchilarga do'stona, "
    "qisqa va aniq javob ber. Javoblaringni asosan o'zbek tilida yoz, "
    "agar foydalanuvchi boshqa tilda yozsa, o'sha tilda javob ber."
)

MODEL = "claude-sonnet-4-6"

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

bot = Bot(token=TELEGRAM_BOT_TOKEN)
dp = Dispatcher()
claude = Anthropic(api_key=ANTHROPIC_API_KEY)

# Har bir foydalanuvchi uchun suhbat tarixi (RAM'da, oddiy versiya)
user_histories: dict[int, list[dict]] = {}
MAX_HISTORY = 20  # necha ta oxirgi xabarni eslab qolish


@dp.message(CommandStart())
async def start_handler(message: Message):
    user_histories[message.from_user.id] = []
    await message.answer(
        "Salom! Men mona_ibot 🤖\n"
        "Menga istalgan savolingizni yozing — AI yordamida javob beraman."
    )


@dp.message(F.text)
async def handle_message(message: Message):
    user_id = message.from_user.id
    text = message.text

    history = user_histories.setdefault(user_id, [])
    history.append({"role": "user", "content": text})
    history = history[-MAX_HISTORY:]

    await bot.send_chat_action(message.chat.id, "typing")

    try:
        response = claude.messages.create(
            model=MODEL,
            max_tokens=1000,
            system=SYSTEM_PROMPT,
            messages=history,
        )
        answer = "".join(
            block.text for block in response.content if block.type == "text"
        ).strip()
        if not answer:
            answer = "Kechirasiz, javob shakllantira olmadim. Qayta urinib ko'ring."
    except Exception as e:
        logger.exception("Claude API xatosi")
        answer = "Kechirasiz, hozir AI bilan bog'lanishda xatolik yuz berdi. Birozdan so'ng qayta urinib ko'ring."

    history.append({"role": "assistant", "content": answer})
    user_histories[user_id] = history[-MAX_HISTORY:]

    await message.answer(answer)


async def main():
    logger.info("mona_ibot ishga tushdi...")
    await dp.start_polling(bot)


if __name__ == "__main__":
    asyncio.run(main())
