import os
import re
import json
import html
import asyncio
import requests
import feedparser
import anthropic
from datetime import time, datetime
from zoneinfo import ZoneInfo
from telegram import Update, LinkPreviewOptions
from telegram.constants import ParseMode
from telegram.ext import Application, MessageHandler, ContextTypes, filters

TOKEN = os.environ["TELEGRAM_TOKEN"]
CHAT_ID = -5570801890
TZ = ZoneInfo("Europe/Athens")
FEEDS = {
    "ERT News": "https://www.ertnews.gr/feed/",
    "in.gr": "https://www.in.gr/feed/",
}

client = anthropic.Anthropic(api_key=os.environ["ANTHROPIC_API_KEY"])
MODEL = "claude-sonnet-5"
NUMBERS = ["1️⃣", "2️⃣", "3️⃣"]


def ask_claude(prompt: str, max_tokens: int = 2000, web_search: bool = False) -> str:
    kwargs = dict(
        model=MODEL,
        max_tokens=max_tokens,
        messages=[{"role": "user", "content": prompt}],
    )
    if web_search:
        kwargs["tools"] = [{"type": "web_search_20250305", "name": "web_search"}]
    resp = client.messages.create(**kwargs)
    return "".join(b.text for b in resp.content if b.type == "text")


def clean(text: str) -> str:
    return html.unescape(re.sub(r"<[^>]+>", "", text or "")).strip()


def fetch_articles(limit_per_feed=15):
    articles = []
    headers = {"User-Agent": "Mozilla/5.0 (compatible; NewsBot/1.0)"}
    for source, url in FEEDS.items():
        try:
            resp = requests.get(url, headers=headers, timeout=10)
            resp.raise_for_status()
            feed = feedparser.parse(resp.content)
        except Exception as e:
            print(f"Skipping {source}: {e}")
            continue
        for e in feed.entries[:limit_per_feed]:
            articles.append({
                "id": len(articles),
                "source": source,
                "title": clean(e.get("title", "")),
                "summary": clean(e.get("summary", ""))[:300],
                "link": e.get("link", ""),
            })
    return articles


def pick_top3(articles):
    listing = "\n".join(
        f"[{a['id']}] ({a['source']}) {a['title']}: {a['summary']}" for a in articles
    )
    prompt = (
        "Below are today's headlines from Greek news outlets, each with an id in "
        "square brackets. Pick the 3 most important stories for Greece. "
        "Return ONLY a JSON array of 3 objects, no other text and no code fences. "
        'Each object has: "id" (the number from the list), '
        '"headline" (a short punchy headline in English, max 10 words), '
        '"summary" (1-2 sentences in English), '
        '"emoji" (one emoji that fits the topic).\n\n' + listing
    )
    raw = ask_claude(prompt)
    data = json.loads(raw[raw.index("["): raw.rindex("]") + 1])
    return data[:3]


def build_news_block() -> str:
    articles = fetch_articles()
    by_id = {a["id"]: a for a in articles}
    picks = pick_top3(articles)

    lines = ["🇬🇷 <b>Top 3 news in Greece</b>"]
    for i, p in enumerate(picks):
        art = by_id.get(p.get("id"))
        block = (
            f"{NUMBERS[i]} {html.escape(p.get('emoji', '📰'))} "
            f"<b>{html.escape(p.get('headline', ''))}</b>\n"
            f"{html.escape(p.get('summary', ''))}"
        )
        if art and art["link"]:
            link = html.escape(art["link"], quote=True)
            block += f'\n🔗 <a href="{link}">Read on {html.escape(art["source"])}</a>'
        lines.append(block)
    return "\n\n".join(lines)


def build_macro_block() -> str:
    prompt = (
        "Search for the most recent available values of these Greek economic "
        "indicators: annual inflation rate (CPI), 10-year government bond yield, "
        "unemployment rate, the ECB key interest rate (deposit facility rate, "
        "which applies to Greece as a eurozone member), and annual GDP growth rate. "
        "Return ONLY a JSON array, no other text, no code fences. Each object has: "
        '"label" (short name), "value" (the figure with its unit, e.g. "3.2%"), '
        '"period" (e.g. "August 2026" or "Q2 2026"), "emoji" (one fitting emoji). '
        "Use the most recent officially reported figure for each, even if the "
        "periods differ between indicators."
    )
    raw = ask_claude(prompt, max_tokens=2000, web_search=True)
    data = json.loads(raw[raw.index("["): raw.rindex("]") + 1])

    lines = ["📊 <b>Greece: key economic indicators</b>"]
    for d in data:
        lines.append(
            f"{html.escape(d.get('emoji', '•'))} <b>{html.escape(d.get('label', ''))}:</b> "
            f"{html.escape(d.get('value', ''))} "
            f"<i>({html.escape(d.get('period', ''))})</i>"
        )
    return "\n".join(lines)


def build_message() -> str:
    date = datetime.now(TZ).strftime("%A, %d %B %Y")
    header = f"<i>{html.escape(date)}</i>"
    news = build_news_block()
    macros = build_macro_block()
    return f"{header}\n\n{news}\n\n{macros}"


async def send_daily_news(context: ContextTypes.DEFAULT_TYPE):
    text = await asyncio.to_thread(build_message)
    await context.bot.send_message(
        chat_id=context.job.chat_id,
        text=text,
        parse_mode=ParseMode.HTML,
        link_preview_options=LinkPreviewOptions(is_disabled=True),
    )


async def handle(update: Update, context: ContextTypes.DEFAULT_TYPE):
    msg = update.message
    if not msg or not msg.text:
        return
    if msg.chat_id != CHAT_ID:
        return

    bot_username = context.bot.username
    mentioned = f"@{bot_username}".lower() in msg.text.lower()
    replied_to_bot = (
        msg.reply_to_message
        and msg.reply_to_message.from_user
        and msg.reply_to_message.from_user.id == context.bot.id
    )
    if not (mentioned or replied_to_bot):
        return

    question = msg.text.replace(f"@{bot_username}", "").strip()
    answer = await asyncio.to_thread(ask_claude, question, 2000, True)
    await msg.reply_text(answer)


def main():
    app = Application.builder().token(TOKEN).build()
    app.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, handle))
    app.job_queue.run_daily(send_daily_news, time=time(9, 0, tzinfo=TZ), chat_id=CHAT_ID)
    app.run_polling()


if __name__ == "__main__":
    main()
