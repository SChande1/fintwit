import os
from twikit import Client


class TweetScraper:
    def __init__(self):
        self.client = Client("en-US")
        self._setup_done = False

    async def ensure_setup(self):
        """Load browser cookies to authenticate without login."""
        if self._setup_done:
            return

        auth_token = os.environ["TWITTER_AUTH_TOKEN"]
        ct0 = os.environ["TWITTER_CT0"]

        self.client.set_cookies(
            {"auth_token": auth_token, "ct0": ct0}
        )
        self._setup_done = True

    async def get_user_tweets(self, screen_name, limit=20):
        """Fetch recent tweets from a user's timeline."""
        await self.ensure_setup()

        try:
            user = await self.client.get_user_by_screen_name(screen_name)
        except Exception as e:
            print(f"[scraper] Could not find user @{screen_name}: {e}")
            return []

        tweets = []
        try:
            result = await self.client.get_user_tweets(
                user.id, "Tweets", count=limit
            )
            for tweet in result:
                rt_user = None
                is_retweet = tweet.retweeted_tweet is not None
                if is_retweet and tweet.retweeted_tweet.user:
                    rt_user = tweet.retweeted_tweet.user.screen_name

                # Extract mentioned usernames from tweet text
                mentioned = []
                text = tweet.full_text or tweet.text or ""
                for word in text.split():
                    if word.startswith("@") and len(word) > 1:
                        mentioned.append(word[1:].strip(".:,;!?"))

                tweets.append(
                    {
                        "id": str(tweet.id),
                        "text": text,
                        "created_at": str(tweet.created_at),
                        "user": screen_name,
                        "url": f"https://x.com/{screen_name}/status/{tweet.id}",
                        "likes": tweet.favorite_count or 0,
                        "retweets": tweet.retweet_count or 0,
                        "replies": tweet.reply_count or 0,
                        "is_retweet": is_retweet,
                        "rt_user": rt_user,
                        "mentioned_users": mentioned,
                    }
                )
        except Exception as e:
            print(f"[scraper] Error fetching tweets for @{screen_name}: {e}")

        return tweets
