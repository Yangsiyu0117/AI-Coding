"""Target discovery module"""
import re


class TargetDiscovery:
    """Prometheus target auto-discovery"""

    def __init__(self, datasource):
        self.datasource = datasource
        if hasattr(datasource, 'discover_targets'):
            self.discover = datasource.discover_targets
        else:
            self.discover = datasource.get_targets

    def discover_jobs(self):
        return self.datasource.discover_targets()

    def match_jobs_by_pattern(self, jobs, pattern):
        """Filter jobs by regex pattern"""
        regex = re.compile(pattern)
        matched = {}
        for job_name, info in jobs.items():
            if regex.search(job_name):
                matched[job_name] = info
        return matched

    def suggestion_mapping(self, jobs):
        """Suggest plugin name mapping based on job names"""
        patterns = {
            "node": "node_exporter",
            "process": "process_exporter",
            "cadvisor|docker": "cadvisor",
            "mysql": "mysqld_exporter",
            "redis": "redis_exporter",
            "elasticsearch|es": "elasticsearch",
            "etcd": "etcd",
            "pulsar": "pulsar",
            "minio|s3": "minio",
            "apisix|apisix": "apisix",
        }
        mapping = {}
        for job_name in jobs:
            for pattern, plugin in patterns.items():
                if re.search(pattern, job_name, re.IGNORECASE):
                    mapping[job_name] = plugin
                    break
        return mapping