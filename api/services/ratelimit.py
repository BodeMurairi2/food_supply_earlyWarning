"""In-memory limits for the paid AI endpoints, so a public link cannot drain the OpenRouter/Tavily credits."""

import time
from collections import defaultdict, deque


class RateLimiter:
    def __init__(self, per_client_hour, per_day):
        self.per_client_hour = per_client_hour
        self.per_day = per_day
        self.clients = defaultdict(deque)
        self.all = deque()

    def check(self, client):
        """Record one call; return an error message if a limit is reached, else None."""
        now = time.time()
        calls = self.clients[client]
        while calls and now - calls[0] > 3600:
            calls.popleft()
        while self.all and now - self.all[0] > 86400:
            self.all.popleft()
        if len(self.all) >= self.per_day:
            return f"The daily limit of {self.per_day} AI requests for this demo is reached. Please try again tomorrow."
        if len(calls) >= self.per_client_hour:
            wait = int((3600 - (now - calls[0])) / 60) + 1
            return f"You can run {self.per_client_hour} AI requests per hour. Please try again in about {wait} minutes."
        calls.append(now)
        self.all.append(now)
        return None
