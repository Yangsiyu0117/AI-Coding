"""Prometheus API Client"""
import requests
import base64


class PrometheusClient:
    """Prometheus HTTP API 客户端"""

    def __init__(self, url, auth_enabled=False, username="", password="", headers=None):
        self.url = url.rstrip("/")
        self.auth_enabled = auth_enabled
        self.username = username
        self.password = password
        self.headers = headers or {}

    def _get_headers(self):
        h = dict(self.headers)
        if self.auth_enabled and self.username:
            token = base64.b64encode(f"{self.username}:{self.password}".encode()).decode()
            h["Authorization"] = f"Basic {token}"
        return h

    def _request(self, endpoint, params=None):
        resp = requests.get(
            f"{self.url}/api/v1/{endpoint}",
            params=params,
            headers=self._get_headers(),
            timeout=30
        )
        resp.raise_for_status()
        return resp.json()

    def get_targets(self):
        """Get all scrape targets state"""
        data = self._request("targets")
        return data.get("data", {})

    def query(self, query):
        """Instant query"""
        data = self._request("query", {"query": query})
        return data.get("data", {})

    def query_range(self, query, start, end, step):
        """Range query"""
        data = self._request("query_range", {
            "query": query, "start": start, "end": end, "step": step
        })
        return data.get("data", {})

    def get_alerts(self):
        """Get active alerts"""
        data = self._request("alerts")
        return data.get("data", {}).get("alerts", [])

    def get_alert_rules(self):
        """Get alert rules"""
        data = self._request("rules")
        return data.get("data", {}).get("groups", [])

    def get_series(self, match_pattern, start=None, end=None):
        """Get time series matching a pattern"""
        params = {"match[]": match_pattern}
        if start:
            params["start"] = start
        if end:
            params["end"] = end
        data = self._request("series", params)
        return data.get("data", [])