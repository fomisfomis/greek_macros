import asyncio
from telegram import Bot
from telegram.constants import ParseMode
from telegram import LinkPreviewOptions
import bot as botmodule

async def main():
    text = await asyncio.to_thread(botmodule.build_message)
    tg_bot = Bot(token=botmodule.TOKEN)
    await tg_bot.send_message(
        chat_id=botmodule.CHAT_ID,
        text=text,
        parse_mode=ParseMode.HTML,
        link_preview_options=LinkPreviewOptions(is_disabled=True),
    )
    print("Sent!")

asyncio.run(main())
