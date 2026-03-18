import httpx


def notify(topic: str, title: str, message: str, url: str | None = None):
    """Send a push notification via ntfy.sh."""
    headers = {
        "Title": title,
        "Tags": "chart_with_upwards_trend",
    }
    if url:
        headers["Click"] = url
        headers["Actions"] = f"view, Open Tweet, {url}"

    resp = httpx.post(
        f"https://ntfy.sh/{topic}",
        content=message.encode("utf-8"),
        headers=headers,
        timeout=10,
    )
    resp.raise_for_status()
