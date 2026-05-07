"""
PhantomEye — Username Recon Module
Checks username availability / existence across 30+ platforms.
"""

import time
import threading
from concurrent.futures import ThreadPoolExecutor, as_completed
from dataclasses import dataclass, field
from typing import Optional

import requests
from rich.console import Console
from rich.progress import Progress, SpinnerColumn, TextColumn, BarColumn, TaskProgressColumn

console = Console()

PLATFORMS = {
    "GitHub":        {"url": "https://github.com/{}", "check": "status", "code": 200},
    "GitLab":        {"url": "https://gitlab.com/{}", "check": "status", "code": 200},
    "Twitter/X":     {"url": "https://twitter.com/{}", "check": "status", "code": 200},
    "Instagram":     {"url": "https://www.instagram.com/{}/", "check": "status", "code": 200},
    "Reddit":        {"url": "https://www.reddit.com/user/{}/", "check": "status", "code": 200},
    "TikTok":        {"url": "https://www.tiktok.com/@{}", "check": "status", "code": 200},
    "YouTube":       {"url": "https://www.youtube.com/@{}", "check": "status", "code": 200},
    "LinkedIn":      {"url": "https://www.linkedin.com/in/{}", "check": "status", "code": 200},
    "Pinterest":     {"url": "https://www.pinterest.com/{}", "check": "status", "code": 200},
    "Twitch":        {"url": "https://www.twitch.tv/{}", "check": "status", "code": 200},
    "Steam":         {"url": "https://steamcommunity.com/id/{}", "check": "text", "needle": "steamcommunity.com/id/"},
    "Keybase":       {"url": "https://keybase.io/{}", "check": "status", "code": 200},
    "HackerNews":    {"url": "https://news.ycombinator.com/user?id={}", "check": "text", "needle": "user?id="},
    "Dev.to":        {"url": "https://dev.to/{}", "check": "status", "code": 200},
    "Medium":        {"url": "https://medium.com/@{}", "check": "status", "code": 200},
    "Gitlab":        {"url": "https://gitlab.com/{}", "check": "status", "code": 200},
    "Bitbucket":     {"url": "https://bitbucket.org/{}", "check": "status", "code": 200},
    "Codepen":       {"url": "https://codepen.io/{}", "check": "status", "code": 200},
    "HackTheBox":    {"url": "https://app.hackthebox.com/profile/overview", "check": "status", "code": 200},
    "TryHackMe":     {"url": "https://tryhackme.com/p/{}", "check": "status", "code": 200},
    "Replit":        {"url": "https://replit.com/@{}", "check": "status", "code": 200},
    "Mastodon":      {"url": "https://mastodon.social/@{}", "check": "status", "code": 200},
    "Telegram":      {"url": "https://t.me/{}", "check": "status", "code": 200},
    "Pastebin":      {"url": "https://pastebin.com/u/{}", "check": "text", "needle": "pastebin.com/u/"},
    "VK":            {"url": "https://vk.com/{}", "check": "status", "code": 200},
    "Flickr":        {"url": "https://www.flickr.com/people/{}", "check": "status", "code": 200},
    "Behance":       {"url": "https://www.behance.net/{}", "check": "status", "code": 200},
    "Dribbble":      {"url": "https://dribbble.com/{}", "check": "status", "code": 200},
    "Soundcloud":    {"url": "https://soundcloud.com/{}", "check": "status", "code": 200},
    "Spotify":       {"url": "https://open.spotify.com/user/{}", "check": "status", "code": 200},
    "Npmjs":         {"url": "https://www.npmjs.com/~{}", "check": "status", "code": 200},
    "PyPI":          {"url": "https://pypi.org/user/{}/", "check": "status", "code": 200},
    "DockerHub":     {"url": "https://hub.docker.com/u/{}", "check": "status", "code": 200},
}

HEADERS = {
    "User-Agent": (
        "Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36 "
        "(KHTML, like Gecko) Chrome/122.0.0.0 Safari/537.36"
    )
}


@dataclass
class PlatformResult:
    platform: str
    found: bool
    url: str
    status_code: Optional[int] = None
    error: Optional[str] = None


class UsernameRecon:
    def __init__(self, timeout: int = 10, max_workers: int = 15):
        self.timeout = timeout
        self.max_workers = max_workers
        self.session = requests.Session()
        self.session.headers.update(HEADERS)

    def _check_platform(self, username: str, platform: str, cfg: dict) -> PlatformResult:
        url = cfg["url"].format(username)
        try:
            resp = self.session.get(url, timeout=self.timeout, allow_redirects=True)
            if cfg["check"] == "status":
                found = resp.status_code == cfg["code"]
            else:  # text needle
                found = cfg["needle"] in resp.text and resp.status_code == 200
            return PlatformResult(platform=platform, found=found, url=url,
                                  status_code=resp.status_code)
        except requests.exceptions.Timeout:
            return PlatformResult(platform=platform, found=False, url=url, error="timeout")
        except requests.exceptions.ConnectionError:
            return PlatformResult(platform=platform, found=False, url=url, error="connection error")
        except Exception as e:
            return PlatformResult(platform=platform, found=False, url=url, error=str(e))

    def run(self, username: str) -> dict:
        results: dict = {"target": username, "platforms": {}}

        with Progress(
            SpinnerColumn(),
            TextColumn("[progress.description]{task.description}"),
            BarColumn(),
            TaskProgressColumn(),
            console=console,
            transient=True,
        ) as progress:
            task = progress.add_task(f"[cyan]Scanning {len(PLATFORMS)} platforms…", total=len(PLATFORMS))

            with ThreadPoolExecutor(max_workers=self.max_workers) as executor:
                futures = {
                    executor.submit(self._check_platform, username, name, cfg): name
                    for name, cfg in PLATFORMS.items()
                }
                for future in as_completed(futures):
                    res: PlatformResult = future.result()
                    results["platforms"][res.platform] = {
                        "found": res.found,
                        "url": res.url,
                        "status_code": res.status_code,
                        "error": res.error,
                    }
                    progress.advance(task)

        found_count = sum(1 for d in results["platforms"].values() if d["found"])
        results["summary"] = {
            "total_platforms": len(PLATFORMS),
            "found": found_count,
            "not_found": len(PLATFORMS) - found_count,
        }
        return results
