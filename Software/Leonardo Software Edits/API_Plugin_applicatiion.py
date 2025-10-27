## This will be the foundation for the API Plugin app so that it can be  Scalable and
 ## will have this ##"Extensible API"## — so that anyone can drop in a new folder under /plugins to add features.


#
import importlib
import LauncherPane.py
from core.hardware_interface import HardwareInterface

class APIManager:
    def __init__(self):
        self.hardware = HardwareInterface()
        self.plugins = {}

    def load_plugins(self):
        plugin_dir = "plugins"
        for folder in os.listdir(plugin_dir):
            path = os.path.join(plugin_dir, folder, "plugin.py")
            if os.path.exists(path):
                module_name = f"plugins.{folder}.plugin"
                module = importlib.import_module(module_name)
                plugin_class = getattr(module, "GlassesPlugin", None)
                if plugin_class:
                    instance = plugin_class(self.hardware)
                    self.plugins[folder] = instance
                    print(f"Loaded plugin: {folder}")

    def start_plugin(self, name):
        if name in self.plugins:
            self.plugins[name].on_start()
            print(f"Started plugin: {name}")

    def stop_plugin(self, name):
        if name in self.plugins:
            self.plugins[name].on_stop()
            print(f"Stopped plugin: {name}")

    def broadcast_event(self, event_type, data):
        for plugin in self.plugins.values():
            plugin.on_event(event_type, data)
