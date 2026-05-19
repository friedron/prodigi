from collections import defaultdict
import time


class RateLimiter:
    def __init__(self, max_requests, window_seconds):
        self.max_requests = max_requests
        self.window_seconds = window_seconds
        self.clients = defaultdict(list)  # Tracks request timestamps for each client

    def is_allowed(self, sid):
        now = time.time()
        request_times = self.clients[sid]

        # Remove timestamps outside the time window
        while request_times and now - request_times[0] > self.window_seconds:
            request_times.pop(0)

        if len(request_times) < self.max_requests:
            request_times.append(now)
            return True  # Allow the request
        return False  # Deny the request