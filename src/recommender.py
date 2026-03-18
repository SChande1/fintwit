def get_recommendations(
    daily_tweets: list,
    mentioned_accounts: dict,
    current_following: list[str],
) -> list[tuple[str, int]]:
    """
    Recommend accounts to follow based on who the monitored accounts
    mention, retweet, or reply to most frequently.
    """
    following_lower = {a.lower() for a in current_following}
    mention_counts: dict[str, int] = {}

    # Count from today's tweets
    for tweet in daily_tweets:
        # Mentioned users
        for user in tweet.get("mentioned_users", []):
            if user.lower() not in following_lower:
                mention_counts[user] = mention_counts.get(user, 0) + 1

        # Retweeted user
        rt_user = tweet.get("rt_user")
        if rt_user and rt_user.lower() not in following_lower:
            mention_counts[rt_user] = mention_counts.get(rt_user, 0) + 2  # weight RTs higher

    # Blend in historical mention data
    for user, count in mentioned_accounts.items():
        if user.lower() not in following_lower:
            mention_counts[user] = mention_counts.get(user, 0) + count

    ranked = sorted(mention_counts.items(), key=lambda x: x[1], reverse=True)
    return ranked[:5]
