"""Instance filtering module"""
import re


class InstanceFilter:
    """Filter instances by whitelist, blacklist, label, or health criteria"""

    def __init__(self, filter_config=None):
        self.config = filter_config or {}

    def filter_instances(self, instances):
        """Apply all configured filters to a list of instances"""
        if not self.config:
            return instances

        result = instances

        whitelist = self.config.get("whitelist", [])
        if whitelist:
            patterns = [re.compile(p) for p in whitelist]
            result = [i for i in result if any(p.search(i.get("instance", "")) for p in patterns)]

        blacklist = self.config.get("blacklist", [])
        if blacklist:
            patterns = [re.compile(p) for p in blacklist]
            result = [i for i in result if not any(p.search(i.get("instance", "")) for p in patterns)]

        health_filter = self.config.get("health", "")
        if health_filter == "up":
            result = [i for i in result if i.get("health") == "up"]
        elif health_filter == "down":
            result = [i for i in result if i.get("health") != "up"]

        include_labels = self.config.get("labels", {})
        if include_labels:
            def _match_labels(inst):
                inst_labels = inst.get("labels", {})
                return all(
                    inst_labels.get(k) == v
                    for k, v in include_labels.items()
                )
            result = [i for i in result if _match_labels(i)]

        return result