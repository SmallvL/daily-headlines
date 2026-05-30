"""Plugin registry for managing source plugins."""
from __future__ import annotations

import importlib
import logging
from pathlib import Path
from typing import Dict, List, Optional, Type

from app.plugins.base import SourcePlugin, AuthMethod

logger = logging.getLogger(__name__)


class PluginRegistry:
    """Central registry for source plugins.
    
    Plugins are automatically discovered and registered from the plugins directory.
    Each plugin must be a subclass of SourcePlugin with a unique plugin_id.
    """
    
    _instance: Optional[PluginRegistry] = None
    _plugins: Dict[str, SourcePlugin] = {}
    
    def __new__(cls) -> PluginRegistry:
        if cls._instance is None:
            cls._instance = super().__new__(cls)
            cls._instance._plugins = {}
        return cls._instance
    
    @classmethod
    def get_instance(cls) -> PluginRegistry:
        """Get singleton instance."""
        return cls()
    
    def register(self, plugin: SourcePlugin) -> None:
        """Register a plugin.
        
        Args:
            plugin: Plugin instance to register
        
        Raises:
            ValueError: If plugin_id is already registered
        """
        if plugin.plugin_id in self._plugins:
            raise ValueError(f"Plugin '{plugin.plugin_id}' is already registered")
        
        self._plugins[plugin.plugin_id] = plugin
        logger.info(f"Registered plugin: {plugin.plugin_id} ({plugin.display_name})")
    
    def get(self, plugin_id: str) -> Optional[SourcePlugin]:
        """Get plugin by ID.
        
        Args:
            plugin_id: Plugin identifier
        
        Returns:
            Plugin instance or None
        """
        return self._plugins.get(plugin_id)
    
    def list_plugins(self) -> List[Dict[str, str]]:
        """List all registered plugins.
        
        Returns:
            List of plugin metadata dicts
        """
        return [
            {
                "id": p.plugin_id,
                "name": p.display_name,
                "description": p.description,
                "icon_url": p.icon_url,
                "auth_methods": [m.value for m in p.supported_auth_methods],
                "source_type": p.default_source_type
            }
            for p in self._plugins.values()
        ]
    
    def get_plugins_by_auth_method(self, method: AuthMethod) -> List[SourcePlugin]:
        """Get plugins that support a specific auth method.
        
        Args:
            method: Authentication method
        
        Returns:
            List of matching plugins
        """
        return [
            p for p in self._plugins.values()
            if method in p.supported_auth_methods
        ]
    
    def discover_plugins(self, plugins_dir: Optional[Path] = None) -> None:
        """Auto-discover and register plugins from directory.
        
        Args:
            plugins_dir: Directory to scan for plugins (default: parent of this file)
        """
        if plugins_dir is None:
            plugins_dir = Path(__file__).parent.parent  # plugins/ directory, not plugins/base/
        
        for plugin_dir in plugins_dir.iterdir():
            if not plugin_dir.is_dir():
                continue
            if plugin_dir.name.startswith('_') or plugin_dir.name == 'base':
                continue
            
            try:
                # Try to import the plugin module
                module_name = f"app.plugins.{plugin_dir.name}"
                module = importlib.import_module(module_name)
                
                # Look for plugin class
                if hasattr(module, 'Plugin'):
                    plugin_class = getattr(module, 'Plugin')
                    if (isinstance(plugin_class, type) and 
                        issubclass(plugin_class, SourcePlugin) and 
                        plugin_class is not SourcePlugin):
                        plugin_instance = plugin_class()
                        if plugin_instance.plugin_id:
                            self.register(plugin_instance)
                            
            except Exception as e:
                logger.warning(f"Failed to load plugin from {plugin_dir.name}: {e}")


# Singleton instance
plugin_registry = PluginRegistry()


def get_plugin_registry() -> PluginRegistry:
    """Get the plugin registry instance."""
    return plugin_registry


def auto_discover_plugins() -> None:
    """Auto-discover all plugins."""
    plugin_registry.discover_plugins()
