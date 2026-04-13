import json
import os

import httpx

BEARER = "AAAAAAAAAAAAAAAAAAAAANRILgAAAAAAnNwIzUejRCOuH5E6I8xnZz4puTs%3D1Zv7ttfk8LF81IUq16cHjhLTvJu4FA33AGWWjCpTnA"
USER_TWEETS_QID = "H8OOoI-5ZE4NxgRr8lfyWg"
USER_BY_SCREEN_NAME_QID = "laYnJPCAcVo0o6pzcnlVxQ"
SEARCH_TIMELINE_QID = "HgiQ8U_E6g-HE_I6Pp_2UA"

FEATURES = {
    "rweb_tipjar_consumption_enabled": True,
    "responsive_web_graphql_exclude_directive_enabled": True,
    "verified_phone_label_enabled": False,
    "creator_subscriptions_tweet_preview_api_enabled": True,
    "responsive_web_graphql_timeline_navigation_enabled": True,
    "responsive_web_graphql_skip_user_profile_image_extensions_enabled": False,
    "communities_web_enable_tweet_community_results_fetch": True,
    "c9s_tweet_anatomy_moderator_badge_enabled": True,
    "articles_preview_enabled": True,
    "responsive_web_edit_tweet_api_enabled": True,
    "graphql_is_translatable_rweb_tweet_is_translatable_enabled": True,
    "view_counts_everywhere_api_enabled": True,
    "longform_notetweets_consumption_enabled": True,
    "responsive_web_twitter_article_tweet_consumption_enabled": True,
    "tweet_awards_web_tipping_enabled": False,
    "creator_subscriptions_quote_tweet_preview_enabled": False,
    "freedom_of_speech_not_reach_fetch_enabled": True,
    "standardized_nudges_misinfo": True,
    "tweet_with_visibility_results_prefer_gql_limited_actions_policy_enabled": True,
    "rweb_video_timestamps_enabled": True,
    "longform_notetweets_rich_text_read_enabled": True,
    "longform_notetweets_inline_media_enabled": True,
    "responsive_web_enhance_cards_enabled": False,
}


class TweetScraper:
    def __init__(self):
        auth_token = os.environ["TWITTER_AUTH_TOKEN"]
        ct0 = os.environ["TWITTER_CT0"]
        self.client = httpx.AsyncClient(
            headers={
                "authorization": f"Bearer {BEARER}",
                "x-csrf-token": ct0,
                "user-agent": (
                    "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
                    "AppleWebKit/537.36 (KHTML, like Gecko) "
                    "Chrome/131.0.0.0 Safari/537.36"
                ),
            },
            cookies={"auth_token": auth_token, "ct0": ct0},
            timeout=20,
        )
        self._user_id_cache: dict[str, str] = {}

    async def _get_user_id(self, screen_name: str) -> str | None:
        if screen_name in self._user_id_cache:
            return self._user_id_cache[screen_name]

        variables = json.dumps({"screen_name": screen_name})
        params = {"variables": variables, "features": json.dumps(FEATURES)}
        url = f"https://api.x.com/graphql/{USER_BY_SCREEN_NAME_QID}/UserByScreenName"

        r = await self.client.get(url, params=params)
        if r.status_code != 200:
            print(f"[scraper] UserByScreenName failed for @{screen_name}: {r.status_code}")
            return None

        data = r.json()
        try:
            rest_id = data["data"]["user"]["result"]["legacy"]["id_str"]
        except (KeyError, TypeError):
            try:
                rest_id = str(data["data"]["user"]["result"]["rest_id"])
            except (KeyError, TypeError):
                print(f"[scraper] Could not extract user ID for @{screen_name}")
                return None

        self._user_id_cache[screen_name] = rest_id
        return rest_id

    async def get_user_tweets(self, screen_name: str, limit: int = 20) -> list[dict]:
        user_id = await self._get_user_id(screen_name)
        if not user_id:
            return []

        variables = json.dumps({
            "userId": user_id,
            "count": limit,
            "includePromotedContent": False,
            "withQuickPromoteEligibilityTweetFields": False,
            "withVoice": False,
            "withV2Timeline": True,
        })
        params = {"variables": variables, "features": json.dumps(FEATURES)}
        url = f"https://api.x.com/graphql/{USER_TWEETS_QID}/UserTweets"

        try:
            r = await self.client.get(url, params=params)
        except Exception as e:
            print(f"[scraper] Request failed for @{screen_name}: {e}")
            return []

        if r.status_code != 200:
            print(f"[scraper] UserTweets failed for @{screen_name}: {r.status_code} {r.text[:200]}")
            return []

        return self._parse_timeline(r.json(), screen_name)

    async def search_tweets(self, query: str, limit: int = 20) -> list[dict]:
        variables = json.dumps({
            "rawQuery": query,
            "count": limit,
            "querySource": "typed_query",
            "product": "Latest",
        })
        params = {"variables": variables, "features": json.dumps(FEATURES)}
        url = f"https://api.x.com/graphql/{SEARCH_TIMELINE_QID}/SearchTimeline"

        try:
            r = await self.client.get(url, params=params)
        except Exception as e:
            print(f"[scraper] Search request failed for '{query}': {e}")
            return []

        if r.status_code != 200:
            print(f"[scraper] Search failed for '{query}': {r.status_code} {r.text[:200]}")
            return []

        return self._parse_search_results(r.json(), query)

    def _parse_search_results(self, data: dict, query: str) -> list[dict]:
        tweets = []
        try:
            instructions = (
                data["data"]["search_by_raw_query"]["search_timeline"]["timeline"]["instructions"]
            )
        except (KeyError, TypeError):
            print(f"[scraper] Unexpected search response structure for '{query}'")
            return []

        for instruction in instructions:
            for entry in instruction.get("entries", []):
                content = entry.get("content", {})
                item = content.get("itemContent", {})
                tweet_res = item.get("tweet_results", {}).get("result", {})

                if tweet_res.get("__typename") == "TweetWithVisibilityResults":
                    tweet_res = tweet_res.get("tweet", {})

                if not tweet_res or "legacy" not in tweet_res:
                    continue

                legacy = tweet_res["legacy"]
                tweet_id = legacy.get("id_str", "")
                full_text = legacy.get("full_text", "")

                # Extract screen_name from the tweet's core user data
                screen_name = (
                    tweet_res.get("core", {})
                    .get("user_results", {})
                    .get("result", {})
                    .get("legacy", {})
                    .get("screen_name", "unknown")
                )

                rt_legacy = legacy.get("retweeted_status_result", {}).get("result", {}).get("legacy", {})
                is_retweet = bool(rt_legacy)
                rt_user = None
                if is_retweet:
                    rt_core = legacy.get("retweeted_status_result", {}).get("result", {}).get("core", {})
                    rt_user = (
                        rt_core.get("user_results", {})
                        .get("result", {})
                        .get("legacy", {})
                        .get("screen_name")
                    )

                mentioned = []
                entities = legacy.get("entities", {})
                for mention in entities.get("user_mentions", []):
                    mentioned.append(mention.get("screen_name", ""))

                tweets.append({
                    "id": tweet_id,
                    "text": full_text,
                    "created_at": legacy.get("created_at", ""),
                    "user": screen_name,
                    "url": f"https://x.com/{screen_name}/status/{tweet_id}",
                    "likes": legacy.get("favorite_count", 0),
                    "retweets": legacy.get("retweet_count", 0),
                    "replies": legacy.get("reply_count", 0),
                    "is_retweet": is_retweet,
                    "rt_user": rt_user,
                    "mentioned_users": mentioned,
                    "matched_keyword": query,
                })

        return tweets

    def _parse_timeline(self, data: dict, screen_name: str) -> list[dict]:
        tweets = []
        try:
            instructions = (
                data["data"]["user"]["result"]["timeline_v2"]["timeline"]["instructions"]
            )
        except (KeyError, TypeError):
            print(f"[scraper] Unexpected response structure for @{screen_name}")
            return []

        for instruction in instructions:
            for entry in instruction.get("entries", []):
                content = entry.get("content", {})
                item = content.get("itemContent", {})
                tweet_res = item.get("tweet_results", {}).get("result", {})

                # Handle "tweet" type (normal) vs "tweetWithVisibilityResults"
                if tweet_res.get("__typename") == "TweetWithVisibilityResults":
                    tweet_res = tweet_res.get("tweet", {})

                if not tweet_res or "legacy" not in tweet_res:
                    continue

                legacy = tweet_res["legacy"]
                tweet_id = legacy.get("id_str", "")
                full_text = legacy.get("full_text", "")

                # Retweet detection
                rt_legacy = legacy.get("retweeted_status_result", {}).get("result", {}).get("legacy", {})
                is_retweet = bool(rt_legacy)
                rt_user = None
                if is_retweet:
                    rt_core = legacy.get("retweeted_status_result", {}).get("result", {}).get("core", {})
                    rt_user = (
                        rt_core.get("user_results", {})
                        .get("result", {})
                        .get("legacy", {})
                        .get("screen_name")
                    )

                # Extract mentions
                mentioned = []
                entities = legacy.get("entities", {})
                for mention in entities.get("user_mentions", []):
                    mentioned.append(mention.get("screen_name", ""))

                tweets.append({
                    "id": tweet_id,
                    "text": full_text,
                    "created_at": legacy.get("created_at", ""),
                    "user": screen_name,
                    "url": f"https://x.com/{screen_name}/status/{tweet_id}",
                    "likes": legacy.get("favorite_count", 0),
                    "retweets": legacy.get("retweet_count", 0),
                    "replies": legacy.get("reply_count", 0),
                    "is_retweet": is_retweet,
                    "rt_user": rt_user,
                    "mentioned_users": mentioned,
                })

        return tweets
