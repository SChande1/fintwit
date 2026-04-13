import httpx


def notify(topic: str, title: str, message: str, url: str | None = None):
    """Send a push notification via ntfy.sh.

    Uses ntfy's JSON publish API (POST body) rather than header fields so
    that non-ASCII characters (emoji, em-dashes, etc.) in the title or
    message don't crash httpx's header encoder.
    """
    payload: dict = {
        "topic": topic,
        "title": title,
        "message": message,
        "tags": ["chart_with_upwards_trend"],
    }
    if url:
        payload["click"] = url
        payload["actions"] = [
            {"action": "view", "label": "Open Tweet", "url": url},
        ]

    resp = httpx.post("https://ntfy.sh/", json=payload, timeout=10)
    resp.raise_for_status()
