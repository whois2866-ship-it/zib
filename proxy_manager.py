"""
Proxy rotation module.
Supports Webshare format (host:port:user:pass) and standard URL format.
"""
 
import random
from config import Config
 
 
class ProxyManager:
    def __init__(self, filepath: str = "proxies.txt"):
        self.proxies: list[dict] = []
        self.index = 0
        self.rotating_url = Config.ROTATING_PROXY_URL
        self._load(filepath)
 
    def _parse_proxy(self, line: str) -> dict | None:
        """Parse proxy line. Supports:
        - Webshare: host:port:user:pass
        - URL: http://user:pass@host:port
        """
        line = line.strip()
        if not line or line.startswith("#"):
            return None
 
        if line.startswith("http://") or line.startswith("https://") or line.startswith("socks5://"):
            return {"server": line}
 
        parts = line.split(":")
        if len(parts) == 4:
            host, port, user, password = parts
            return {
                "server": f"http://{host}:{port}",
                "username": user,
                "password": password,
            }
        elif len(parts) == 2:
            host, port = parts
            return {"server": f"http://{host}:{port}"}
 
        return None
 
    def _load(self, filepath: str):
        try:
            with open(filepath) as f:
                for line in f:
                    proxy = self._parse_proxy(line)
                    if proxy:
                        self.proxies.append(proxy)
            print(f"Loaded {len(self.proxies)} proxies from {filepath}")
        except FileNotFoundError:
            if Config.PROXY_URL:
                self.proxies = [{"server": Config.PROXY_URL}]
                print("Using single proxy from .env")
            else:
                print("No proxies configured. Running without proxy.")
 
    def next(self) -> dict | None:
        """Get the next proxy in rotation (Playwright format)."""
        if self.rotating_url:
            return {"server": self.rotating_url}
        if not self.proxies:
            return None
        proxy = self.proxies[self.index % len(self.proxies)]
        self.index += 1
        return proxy
 
    def random(self) -> dict | None:
        """Get a random proxy from the list."""
        if self.rotating_url:
            return {"server": self.rotating_url}
        if not self.proxies:
            return None
        return random.choice(self.proxies)
 
    def remove_current(self):
        """Remove the most recently returned proxy."""
        if self.proxies and self.index > 0:
            idx = (self.index - 1) % len(self.proxies)
            self.proxies.pop(idx)
            print(f"Removed dead proxy. {len(self.proxies)} remaining.")
 
    def remaining(self) -> int:
        return len(self.proxies)
