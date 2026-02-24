"""
Configuration management for OpenGameBoost.
"""
import json
import os
import logging
from typing import Dict, Any

logger = logging.getLogger(__name__)

DEFAULT_CONFIG = {
    "general": {
        "start_minimized": False,
        "start_with_windows": False,
        "minimize_to_tray": True,
        "check_updates": True,
    },
    "game_detector": {
        "enabled": False,
        "auto_optimize": True,
        "check_interval": 5,
    },
    "memory": {
        "enabled": True,
        "auto_optimize": True,
        "exclude_processes": [],
    },
    "network": {
        "enabled": True,
        "disable_nagle": True,
        "disable_netbios": True,
        "optimize_dns": True,
    },
    "power": {
        "enabled": True,
        "auto_switch": True,
    },
    "registry": {
        "enabled": True,
        "gpu_priority": True,
        "game_bar": True,
        "mouse_optimization": True,
    },
}


class Config:
    """Configuration manager for OpenGameBoost."""
    
    def __init__(self, config_path: str = None):
        if config_path is None:
            # Use AppData folder on Windows
            appdata = os.environ.get('APPDATA', os.path.expanduser('~'))
            config_dir = os.path.join(appdata, 'OpenGameBoost')
            os.makedirs(config_dir, exist_ok=True)
            self.config_path = os.path.join(config_dir, 'config.json')
        else:
            self.config_path = config_path
        
        self.config: Dict[str, Any] = {}
        self.load()
    
    def _deep_copy_defaults(self) -> Dict[str, Any]:
        """Create a deep copy of DEFAULT_CONFIG to prevent mutation."""
        return json.loads(json.dumps(DEFAULT_CONFIG))
    
    def load(self) -> bool:
        """Load configuration from file."""
        try:
            if os.path.exists(self.config_path):
                with open(self.config_path, 'r') as f:
                    self.config = json.load(f)
                # Merge with defaults to ensure all keys exist
                self._merge_defaults()
                logger.info(f"Configuration loaded from {self.config_path}")
                return True
            else:
                self.config = self._deep_copy_defaults()
                self.save()
                logger.info("Created default configuration")
                return True
        except Exception as e:
            logger.error(f"Error loading configuration: {e}")
            self.config = self._deep_copy_defaults()
            return False
    
    def save(self) -> bool:
        """Save configuration to file."""
        try:
            with open(self.config_path, 'w') as f:
                json.dump(self.config, f, indent=2)
            logger.info(f"Configuration saved to {self.config_path}")
            return True
        except Exception as e:
            logger.error(f"Error saving configuration: {e}")
            return False
    
    def _merge_defaults(self):
        """Merge loaded config with defaults to ensure all keys exist."""
        def merge_dict(base: dict, override: dict) -> dict:
            result = base.copy()
            for key, value in override.items():
                if key in result and isinstance(result[key], dict) and isinstance(value, dict):
                    result[key] = merge_dict(result[key], value)
                else:
                    result[key] = value
            return result
        
        self.config = merge_dict(DEFAULT_CONFIG, self.config)
    
    def get(self, section: str, key: str = None, default: Any = None) -> Any:
        """Get a configuration value."""
        try:
            if key is None:
                return self.config.get(section, default)
            return self.config.get(section, {}).get(key, default)
        except Exception:
            return default
    
    def set(self, section: str, key: str, value: Any):
        """Set a configuration value."""
        if section not in self.config:
            self.config[section] = {}
        self.config[section][key] = value
    
    def reset_to_defaults(self):
        """Reset all configuration to defaults."""
        self.config = self._deep_copy_defaults()
        self.save()
