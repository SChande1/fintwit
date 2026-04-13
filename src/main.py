"""
FinTwit Monitor — check for new tweets, notify, and send daily summaries.

Usage:
    python -m src.main accounts   # fetch followed accounts & notify (+ summary)
    python -m src.main keywords   # run keyword search & notify
    python -m src.main summary    # force-send the daily summary now
    python -m src.main all        # accounts + keywords + summary (legacy)
"""

import asyncio
import os
import sys
from datetime import datetime, timezone, timedelta

from .scraper import TweetScraper
from .notifier import notify
from .emailer import send_email
from .summarizer import generate_summary_html
from .recommender import get_recommendations
from .state import load_state, save_state

CST = timezone(timedelta(hours=-6))
SUMMARY_HOUR = 22  # 10 PM CST


def _load_config() -> dict:
    import json

    with open(os.path.join(os.path.dirname(__file__), "..", "config.json")) as f:
        return json.load(f)


async def check_accounts():
    """Fetch new tweets from monitored accounts and send notifications."""
    config = _load_config()
    state = load_state()
    ntfy_topic = os.environ.get("NTFY_TOPIC", "fintwit_default")

    scraper = TweetScraper()
    new_count = 0

    for account in config["accounts"]:
        print(f"[accounts] Fetching tweets for @{account}...")
        tweets = await scraper.get_user_tweets(account, limit=20)

        for tweet in tweets:
            if tweet["id"] in state["seen_ids"]:
                continue

            new_count += 1
            state["seen_ids"].append(tweet["id"])
            state["daily_tweets"].append(tweet)

            # Track mentioned / retweeted accounts
            for user in tweet.get("mentioned_users", []):
                state["mentioned_accounts"][user] = (
                    state["mentioned_accounts"].get(user, 0) + 1
                )
            rt_user = tweet.get("rt_user")
            if rt_user:
                state["mentioned_accounts"][rt_user] = (
                    state["mentioned_accounts"].get(rt_user, 0) + 2
                )

            # Push notification
            try:
                text_preview = tweet["text"][:300]
                if len(tweet["text"]) > 300:
                    text_preview += "..."
                notify(ntfy_topic, f"@{tweet['user']}", text_preview, tweet["url"])
                print(f"  -> notified: {tweet['id']}")
            except Exception as e:
                print(f"  -> notification failed: {e}")

    # Keep seen_ids from growing forever (retain last 2000)
    state["seen_ids"] = state["seen_ids"][-2000:]

    save_state(state)
    print(f"[accounts] Done. {new_count} new tweet(s) found.")


async def check_keywords():
    """Run keyword search across all of Twitter and send notifications."""
    config = _load_config()
    state = load_state()
    ntfy_topic = os.environ.get("NTFY_TOPIC", "fintwit_default")

    scraper = TweetScraper()
    new_count = 0

    for keyword in config.get("keywords", []):
        print(f"[keywords] Searching for keyword '{keyword}'...")
        tweets = await scraper.search_tweets(keyword, limit=20)

        for tweet in tweets:
            if tweet["id"] in state["seen_ids"]:
                continue

            new_count += 1
            state["seen_ids"].append(tweet["id"])
            state["daily_tweets"].append(tweet)

            for user in tweet.get("mentioned_users", []):
                state["mentioned_accounts"][user] = (
                    state["mentioned_accounts"].get(user, 0) + 1
                )
            rt_user = tweet.get("rt_user")
            if rt_user:
                state["mentioned_accounts"][rt_user] = (
                    state["mentioned_accounts"].get(rt_user, 0) + 2
                )

            try:
                text_preview = tweet["text"][:300]
                if len(tweet["text"]) > 300:
                    text_preview += "..."
                notify(
                    ntfy_topic,
                    f"🔑 {keyword} — @{tweet['user']}",
                    text_preview,
                    tweet["url"],
                )
                print(f"  -> notified (keyword '{keyword}'): {tweet['id']}")
            except Exception as e:
                print(f"  -> notification failed: {e}")

    state["seen_ids"] = state["seen_ids"][-2000:]
    save_state(state)
    print(f"[keywords] Done. {new_count} new tweet(s) found.")


async def send_summary(force: bool = False):
    """Generate and email the daily summary if it's time (or forced)."""
    config = _load_config()
    state = load_state()

    now = datetime.now(CST)
    today_str = now.strftime("%Y-%m-%d")

    if not force:
        if now.hour != SUMMARY_HOUR:
            print(f"[summary] Not summary time (current hour CST: {now.hour}).")
            return
        if state.get("summary_sent_date") == today_str:
            print("[summary] Already sent today.")
            return

    recommendations = get_recommendations(
        state["daily_tweets"],
        state["mentioned_accounts"],
        config["accounts"],
    )

    html = generate_summary_html(
        state["daily_tweets"],
        state["mentioned_accounts"],
        recommendations,
    )

    subject = f"FinTwit Daily Summary — {now.strftime('%B %d, %Y')}"

    try:
        send_email(config["email"], subject, html)
        print(f"[summary] Email sent to {config['email']}.")
    except Exception as e:
        print(f"[summary] Email failed: {e}")
        return

    # Reset daily state
    state["daily_tweets"] = []
    state["mentioned_accounts"] = {}
    state["summary_sent_date"] = today_str
    save_state(state)


async def run_accounts():
    """Accounts workflow entry point: check accounts, then summary if it's time."""
    await check_accounts()
    await send_summary()


async def run_all():
    """Legacy combined run — accounts + keywords + summary."""
    await check_accounts()
    await check_keywords()
    await send_summary()


def main():
    action = sys.argv[1] if len(sys.argv) > 1 else "all"

    if action == "accounts":
        asyncio.run(run_accounts())
    elif action == "keywords":
        asyncio.run(check_keywords())
    elif action == "summary":
        asyncio.run(send_summary(force=True))
    elif action == "check":
        # Legacy alias for "all" minus summary
        asyncio.run(check_accounts())
        asyncio.run(check_keywords())
    else:
        asyncio.run(run_all())


if __name__ == "__main__":
    main()
