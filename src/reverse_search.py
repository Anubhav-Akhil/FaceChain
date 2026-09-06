"""
reverse_search.py — Stage 3: Reverse image search via SerpAPI (Google Lens).

Takes a public image URL and searches for visually matching content,
prioritizing social media platforms.
"""

from serpapi import Client

from .utils import console


# Domains we consider "social media" — prioritized in results
SOCIAL_MEDIA_DOMAINS = {
    "instagram.com",
    "twitter.com",
    "x.com",
    "facebook.com",
    "linkedin.com",
    "pinterest.com",
    "tiktok.com",
    "reddit.com",
    "tumblr.com",
    "flickr.com",
    "vk.com",
    "youtube.com",
    "threads.net",
}


def _is_social_media(url: str) -> bool:
    """Check if a URL belongs to a known social media platform."""
    url_lower = url.lower()
    return any(domain in url_lower for domain in SOCIAL_MEDIA_DOMAINS)


def _get_domain(url: str) -> str:
    """Extract the domain from a URL."""
    try:
        from urllib.parse import urlparse
        parsed = urlparse(url)
        return parsed.netloc.replace("www.", "")
    except Exception:
        return url


def search_face(image_url: str, api_key: str) -> dict:
    """
    Perform a reverse image search using Google Lens via SerpAPI.

    Parameters
    ----------
    image_url : str
        Public URL of the face image (from ImgBB).
    api_key : str
        SerpAPI API key.

    Returns
    -------
    dict with keys:
        - title      : str — title/description of the matched post
        - link       : str — URL of the matched post
        - source     : str — domain name of the source
        - thumbnail  : str — thumbnail URL (if available)
        - snippet    : str — text snippet (if available)
        - is_social  : bool — whether the match is from social media
        - all_matches: list[dict] — all visual matches found

    Raises
    ------
    RuntimeError — if the search returns no results
    """
    console.print(f"\n[bold cyan]🔍 Stage 3:[/] Reverse Image Search (Google Lens)")
    console.print(f"   Image URL: {image_url}")
    console.print("   Searching…")

    client = Client(api_key=api_key)

    results = client.search({
        "engine": "google_lens",
        "url": image_url,
    })

    # ── Parse visual matches ─────────────────────────────────────
    visual_matches = results.get("visual_matches", [])

    if not visual_matches:
        # Fallback: try "knowledge_graph" or "organic_results"
        knowledge = results.get("knowledge_graph", [])
        if knowledge:
            console.print(
                "   [yellow]No visual matches, but found knowledge graph data.[/]"
            )

        raise RuntimeError(
            "No visual matches found via Google Lens. "
            "The face may not have a recognizable online presence, "
            "or the image quality may be too low."
        )

    console.print(f"   Found [bold green]{len(visual_matches)}[/] visual matches")

    # ── Prioritize social media matches ──────────────────────────
    social_matches = []
    other_matches = []

    for match in visual_matches:
        link = match.get("link", "")
        entry = {
            "title": match.get("title", "Untitled"),
            "link": link,
            "source": match.get("source", _get_domain(link)),
            "thumbnail": match.get("thumbnail", ""),
            "snippet": match.get("snippet", ""),
        }

        if _is_social_media(link):
            social_matches.append(entry)
        else:
            other_matches.append(entry)

    # Pick the best match: social media first, then any match
    if social_matches:
        best = social_matches[0]
        best["is_social"] = True
        console.print(
            f"   [bold green]✓ Social media match found![/]  "
            f"Source: {best['source']}"
        )
    else:
        best = other_matches[0] if other_matches else {
            "title": visual_matches[0].get("title", "Untitled"),
            "link": visual_matches[0].get("link", ""),
            "source": visual_matches[0].get("source", "unknown"),
            "thumbnail": visual_matches[0].get("thumbnail", ""),
            "snippet": visual_matches[0].get("snippet", ""),
        }
        best["is_social"] = False
        console.print(
            f"   [yellow]No social media match — using best web match:[/]  "
            f"Source: {best.get('source', 'unknown')}"
        )

    console.print(f"   Title : {best['title'][:80]}")
    console.print(f"   Link  : {best['link'][:100]}")

    best["all_matches"] = social_matches + other_matches

    return best
