"""Data source abstraction layer"""
from abc import ABC, abstractmethod
from core.prometheus_client import PrometheusClient


class DataSourceConfig:
    """Configuration for a data source"""

    def __init__(self, ds_type="prometheus", url="", auth_enabled=False,
                 username="", password="", headers=None):
        self.ds_type = ds_type
        self.url = url
        self.auth_enabled = auth_enabled
        self.username = username
        self.password = password
        self.headers = headers or {}

    @classmethod
    def from_project(cls, project):
        """Create config from a projects table row"""
        return cls(
            ds_type="prometheus",
            url=project["prometheus_url"],
            auth_enabled=bool(project["auth_enabled"]),
            username=project["auth_username"] or "",
            password=project["auth_password"] or ""
        )


class DataSource(ABC):
    """Abstract interface for monitoring data sources"""

    def __init__(self, config: DataSourceConfig):
        self.config = config

    @abstractmethod
    def query(self, query_str):
        """Execute an instant query"""

    @abstractmethod
    def discover_targets(self):
        """Discover all monitored targets"""

    @abstractmethod
    def get_alerts(self):
        """Get current active alerts"""

    def test_connection(self):
        """Test connectivity — override for richer checks"""
        try:
            self.query("1+1")
            return True, "连接成功"
        except Exception as e:
            return False, str(e)


class PrometheusDataSource(DataSource):
    """Prometheus-backed data source"""

    def __init__(self, config: DataSourceConfig):
        super().__init__(config)
        self._client = PrometheusClient(
            url=config.url,
            auth_enabled=config.auth_enabled,
            username=config.username,
            password=config.password,
            headers=config.headers
        )

    def query(self, query_str):
        return self._client.query(query_str)

    def discover_targets(self):
        targets = self._client.get_targets()
        jobs = {}
        for t in targets.get("activeTargets", []):
            labels = t.get("labels", {})
            job = labels.get("job", "unknown")
            instance = labels.get("instance", "")
            health = t.get("health", "unknown")
            if job not in jobs:
                jobs[job] = {"instances": [], "up": 0, "down": 0}
            jobs[job]["instances"].append({
                "instance": instance,
                "health": health,
                "labels": labels
            })
            if health == "up":
                jobs[job]["up"] += 1
            else:
                jobs[job]["down"] += 1
        return jobs

    def get_alerts(self):
        return self._client.get_alerts()

    def query_range(self, query, start, end, step):
        return self._client.query_range(query, start, end, step)

    def get_series(self, match_pattern, start=None, end=None):
        return self._client.get_series(match_pattern, start, end)


class DataSourceRegistry:
    """Registry of DataSource classes"""

    def __init__(self):
        self._sources = {}

    def register(self, name, cls):
        self._sources[name] = cls

    def get(self, name):
        return self._sources.get(name)

    def create(self, config: DataSourceConfig):
        cls = self.get(config.ds_type)
        if not cls:
            raise ValueError(f"Unknown data source type: {config.ds_type}")
        return cls(config)


# Default registry with built-in types
_default_registry = DataSourceRegistry()
_default_registry.register("prometheus", PrometheusDataSource)


def get_default_registry():
    return _default_registry