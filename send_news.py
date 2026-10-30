import asyncio, sys, json
from datetime import datetime
from telegram import Bot, LinkPreviewOptions
from telegram.constants import ParseMode
import bot

STATE = "sent.json"

def load():
    try:
        with open(STATE) as f:
            return json.load(f)
    except Exception:
        return {}

def save(state):
    with open(STATE, "w") as f:
        json.dump(state, f)

async def send(which):
    build = bot.build_message_gr if which == "gr" else bot.build_message_nl
    text = await asyncio.to_thread(build)
    async with Bot(bot.TOKEN) as b:
        await b.send_message(chat_id=bot.NEWS_CHAT_ID, text=text,
            parse_mode=ParseMode.HTML,
            link_preview_options=LinkPreviewOptions(is_disabled=True))

TZS = {"gr": bot.TZ_GR, "nl": bot.TZ_NL}

def main():
    state = load()
    failed = False
    if len(sys.argv) > 1 and sys.argv[1] in TZS:
        keys = [sys.argv[1]]            # manual run: send now, then record
        force = True
    else:
        keys = ["gr", "nl"]             # scheduled run: only if due and not yet sent today
        force = False
    for key in keys:
        now = datetime.now(TZS[key])
        today = now.date().isoformat()
        due = 8 <= now.hour < 12 and state.get(key) != today
        if force or due:
            try:
                asyncio.run(send(key))
                state[key] = today
                save(state)
            except Exception as e:
                print("FAILED", key, repr(e))
                failed = True
    if failed:
        sys.exit(1)

if __name__ == "__main__":
    main()
