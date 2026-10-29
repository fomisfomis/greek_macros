import asyncio, sys
from datetime import datetime
from telegram import Bot, LinkPreviewOptions
from telegram.constants import ParseMode
import bot

async def send(which):
    build = bot.build_message_gr if which == "gr" else bot.build_message_nl
    text = await asyncio.to_thread(build)
    async with Bot(bot.TOKEN) as b:
        await b.send_message(chat_id=bot.NEWS_CHAT_ID, text=text,
            parse_mode=ParseMode.HTML,
            link_preview_options=LinkPreviewOptions(is_disabled=True))

if __name__ == "__main__":
    if len(sys.argv) > 1:
        asyncio.run(send(sys.argv[1]))
    else:
        if datetime.now(bot.TZ_GR).hour == 8:
            asyncio.run(send("gr"))
        if datetime.now(bot.TZ_NL).hour == 8:
            asyncio.run(send("nl"))
