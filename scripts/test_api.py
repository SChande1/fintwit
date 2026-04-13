import httpx
import json
import os

AUTH_TOKEN = os.environ.get("TWITTER_AUTH_TOKEN", "")
CT0 = os.environ.get("TWITTER_CT0", "")
BEARER = "AAAAAAAAAAAAAAAAAAAAANRILgAAAAAAnNwIzUejRCOuH5E6I8xnZz4puTs%3D1Zv7ttfk8LF81IUq16cHjhLTvJu4FA33AGWWjCpTnA"

headers = {
    "authorization": f"Bearer {BEARER}",
    "x-csrf-token": CT0,
    "user-agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/131.0.0.0 Safari/537.36",
}
cookies = {"auth_token": AUTH_TOKEN, "ct0": CT0}

user_id = "18856867"  # zerohedge

variables = json.dumps({
    "userId": user_id,
    "count": 5,
    "includePromotedContent": False,
    "withQuickPromoteEligibilityTweetFields": False,
    "withVoice": False,
    "withV2Timeline": True,
})

features = json.dumps({
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
})

query_ids = [
    "E3opETHuJmZzHnMaL7GUhQ",
    "H8OOoI-5ZE4NxgRr8lfyWg",
    "eS7LO5Jy3xgmd3dbL044EA",
    "QWF3SzpHmykQHsQMixG0cg",
    "V7H0Ap3_Hh2FyS75OCDO3Q",
    "CdG2Vuc1v6F5JyEngGpxVw",
    "Y04gfaFJCjLBsNJHFHlzDQ",
]

for qid in query_ids:
    url = f"https://api.x.com/graphql/{qid}/UserTweets"
    params = {"variables": variables, "features": features}
    try:
        r = httpx.get(url, headers=headers, cookies=cookies, params=params, timeout=15)
        is_cf = "Cloudflare" in r.text[:200]
        has_data = "tweet_results" in r.text[:5000]
        print(f"{r.status_code} qid={qid} CF={is_cf} hasData={has_data}")
        if has_data and r.status_code == 200:
            print("  WORKING QUERY ID FOUND!")
            data = r.json()
            # Extract a tweet
            instructions = data.get("data", {}).get("user", {}).get("result", {}).get("timeline_v2", {}).get("timeline", {}).get("instructions", [])
            for inst in instructions:
                entries = inst.get("entries", [])
                for entry in entries[:3]:
                    content = entry.get("content", {})
                    item = content.get("itemContent", {})
                    tweet_res = item.get("tweet_results", {}).get("result", {})
                    legacy = tweet_res.get("legacy", {})
                    text = legacy.get("full_text", "")
                    if text:
                        print(f"  TWEET: {text[:200]}")
            break
        elif not is_cf:
            print(f"  Response: {r.text[:200]}")
    except Exception as e:
        print(f"ERROR qid={qid}: {e}")
