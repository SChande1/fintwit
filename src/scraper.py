import os
import twscrape


class TweetScraper:
    def __init__(self, db_path="twscrape.db"):
        self.api = twscrape.API(db_path)
        self._setup_done = False

    async def ensure_setup(self):
        """Add account to pool and login if not already done."""
        if self._setup_done:
            return

        accounts = await self.api.pool.accounts_info()
        if accounts.get("total", 0) == 0:
            username = os.environ["TWITTER_USERNAME"]
            password = os.environ["TWITTER_PASSWORD"]
            email = os.environ.get("TWITTER_EMAIL", "")
            email_password = os.environ.get("TWITTER_EMAIL_PASSWORD", password)
            await self.api.pool.add_account(
                username, password, email, email_password
            )
            await self.api.pool.login_all()

        self._setup_done = True

    async def get_user_tweets(self, screen_name, limit=20):
        """Fetch recent tweets from a user's timeline."""
        await self.ensure_setup()

        try:
            user = await self.api.user_by_login(screen_name)
        except Exception as e:
            print(f"[scraper] Could not find user @{screen_name}: {e}")
            return []

        tweets = []
        try:
            async for tweet in self.api.user_tweets(user.id, limit=limit):
                rt_user = None
                if tweet.retweetedTweet is not None:
                    rt_user = (
                        tweet.retweetedTweet.user.username
                        if tweet.retweetedTweet.user
                        else None
                    )

                mentioned = []
                if tweet.mentionedUsers:
                    mentioned = [u.username for u in tweet.mentionedUsers]

                tweets.append(
                    {
                        "id": str(tweet.id),
                        "text": tweet.rawContent,
                        "created_at": tweet.date.isoformat(),
                        "user": screen_name,
                        "url": f"https://x.com/{screen_name}/status/{tweet.id}",
                        "likes": tweet.likeCount or 0,
                        "retweets": tweet.retweetCount or 0,
                        "replies": tweet.replyCount or 0,
                        "is_retweet": tweet.retweetedTweet is not None,
                        "rt_user": rt_user,
                        "mentioned_users": mentioned,
                    }
                )
        except Exception as e:
            print(f"[scraper] Error fetching tweets for @{screen_name}: {e}")

        return tweets
