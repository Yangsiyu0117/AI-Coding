"""Plugin loader - discovers and loads inspection plugins"""
import importlib
import inspect
import os
import sys
from plugins.base import BasePlugin


class PluginLoader:
    """Plugin discovery and loading engine"""

    def __init__(self, plugin_dir=None):
        if plugin_dir is None:
            plugin_dir = os.path.join(os.path.dirname(__file__), "..", "plugins")
        self.plugin_dir = os.path.abspath(plugin_dir)
        if self.plugin_dir not in sys.path:
            sys.path.insert(0, os.path.dirname(self.plugin_dir))

    def list_available_plugins(self):
        """List all available plugin modules"""
        plugins = {}
        if not os.path.exists(self.plugin_dir):
            return plugins
        for f in sorted(os.listdir(self.plugin_dir)):
            if f.endswith(".py") and not f.startswith("_"):
                name = f[:-3]
                try:
                    module = importlib.import_module(f"plugins.{name}")
                    for attr_name in dir(module):
                        attr = getattr(module, attr_name)
                        if (inspect.isclass(attr) and issubclass(attr, BasePlugin)
                                and attr is not BasePlugin):
                            plugins[name] = attr
                except Exception as e:
                    print(f"Warning: failed to load plugin {name}: {e}")
        return plugins

    def get_plugin(self, plugin_name):
        """Get a single plugin by name"""
        plugins = self.list_available_plugins()
        return plugins.get(plugin_name)

    def get_plugin_class(self, plugin_name):
        """Get plugin class by name"""
        return self.get_plugin(plugin_name)