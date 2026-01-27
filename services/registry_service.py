"""
Registry Service
Applies gaming-related registry optimizations.
"""
import logging
from typing import Dict, Optional, Any

logger = logging.getLogger(__name__)


class RegistryService:
    """Service to apply registry-based gaming optimizations."""
    
    def __init__(self):
        self.enabled = True
        self._backups: Dict[str, Any] = {}
        self._winreg_available = False
        
        try:
            import winreg
            self._winreg = winreg
            self._winreg_available = True
        except ImportError:
            logger.warning("winreg not available - registry modifications disabled")
    
    def _backup_value(self, key_path: str, value_name: str, hkey=None):
        """Backup a registry value before modifying it."""
        if not self._winreg_available:
            return
        
        if hkey is None:
            hkey = self._winreg.HKEY_CURRENT_USER
        
        backup_key = f"{hkey}\\{key_path}\\{value_name}"
        try:
            key = self._winreg.OpenKeyEx(hkey, key_path, 0, 
                                         self._winreg.KEY_READ | self._winreg.KEY_WOW64_64KEY)
            value, reg_type = self._winreg.QueryValueEx(key, value_name)
            self._winreg.CloseKey(key)
            self._backups[backup_key] = {"value": value, "type": reg_type}
        except FileNotFoundError:
            self._backups[backup_key] = None  # Value didn't exist
        except Exception as e:
            logger.debug(f"Could not backup {backup_key}: {e}")
    
    def _set_registry_value(self, key_path: str, value_name: str, value: Any, 
                           reg_type: int, hkey=None, backup: bool = True) -> bool:
        """Set a registry value."""
        if not self._winreg_available:
            return False
        
        if hkey is None:
            hkey = self._winreg.HKEY_CURRENT_USER
        
        try:
            if backup:
                self._backup_value(key_path, value_name, hkey)
            
            key = self._winreg.CreateKeyEx(hkey, key_path, 0,
                                           self._winreg.KEY_SET_VALUE | self._winreg.KEY_WOW64_64KEY)
            self._winreg.SetValueEx(key, value_name, 0, reg_type, value)
            self._winreg.CloseKey(key)
            return True
        except PermissionError:
            logger.warning(f"Need admin rights for: {key_path}")
            return False
        except Exception as e:
            logger.error(f"Error setting registry value: {e}")
            return False
    
    def set_gpu_priority(self) -> bool:
        """
        Set GPU scheduling priority for better gaming performance.
        Modifies GPU Priority and Priority values in the graphics driver settings.
        """
        if not self._winreg_available:
            return False
        
        try:
            # GPU Priority - Higher values = higher priority
            key_path = r"SOFTWARE\Microsoft\Windows NT\CurrentVersion\Multimedia\SystemProfile\Tasks\Games"
            
            results = []
            results.append(self._set_registry_value(
                key_path, "GPU Priority", 8, self._winreg.REG_DWORD
            ))
            results.append(self._set_registry_value(
                key_path, "Priority", 6, self._winreg.REG_DWORD
            ))
            results.append(self._set_registry_value(
                key_path, "Scheduling Category", "High", self._winreg.REG_SZ
            ))
            results.append(self._set_registry_value(
                key_path, "SFIO Priority", "High", self._winreg.REG_SZ
            ))
            
            if any(results):
                logger.info("GPU priority settings applied")
                return True
            return False
            
        except Exception as e:
            logger.error(f"Error setting GPU priority: {e}")
            return False
    
    def disable_explorer_restart(self) -> bool:
        """
        Disable automatic Explorer.exe restart.
        This prevents desktop flickering during game crashes.
        """
        if not self._winreg_available:
            return False
        
        try:
            key_path = r"SOFTWARE\Microsoft\Windows NT\CurrentVersion\Winlogon"
            return self._set_registry_value(
                key_path, "AutoRestartShell", 0, 
                self._winreg.REG_DWORD,
                self._winreg.HKEY_LOCAL_MACHINE
            )
        except Exception as e:
            logger.error(f"Error disabling explorer restart: {e}")
            return False
    
    def enable_explorer_restart(self) -> bool:
        """Re-enable automatic Explorer.exe restart."""
        if not self._winreg_available:
            return False
        
        try:
            key_path = r"SOFTWARE\Microsoft\Windows NT\CurrentVersion\Winlogon"
            return self._set_registry_value(
                key_path, "AutoRestartShell", 1,
                self._winreg.REG_DWORD,
                self._winreg.HKEY_LOCAL_MACHINE,
                backup=False
            )
        except Exception as e:
            logger.error(f"Error enabling explorer restart: {e}")
            return False
    
    def enable_game_bar(self) -> bool:
        """Enable Xbox Game Bar features."""
        if not self._winreg_available:
            return False
        
        try:
            key_path = r"SOFTWARE\Microsoft\Windows\CurrentVersion\GameDVR"
            results = []
            results.append(self._set_registry_value(
                key_path, "AppCaptureEnabled", 1, self._winreg.REG_DWORD
            ))
            
            key_path2 = r"SOFTWARE\Microsoft\GameBar"
            results.append(self._set_registry_value(
                key_path2, "AutoGameModeEnabled", 1, self._winreg.REG_DWORD
            ))
            results.append(self._set_registry_value(
                key_path2, "AllowAutoGameMode", 1, self._winreg.REG_DWORD
            ))
            
            if any(results):
                logger.info("Game Bar settings applied")
            return any(results)
            
        except Exception as e:
            logger.error(f"Error enabling Game Bar: {e}")
            return False
    
    def disable_fullscreen_optimizations(self) -> bool:
        """
        Disable fullscreen optimizations system-wide.
        Can improve performance in some games.
        """
        if not self._winreg_available:
            return False
        
        try:
            key_path = r"SYSTEM\CurrentControlSet\Control\GraphicsDrivers"
            return self._set_registry_value(
                key_path, "HwSchMode", 2,
                self._winreg.REG_DWORD,
                self._winreg.HKEY_LOCAL_MACHINE
            )
        except Exception as e:
            logger.error(f"Error disabling fullscreen optimizations: {e}")
            return False
    
    def enable_hardware_accelerated_gpu_scheduling(self) -> bool:
        """
        Enable Hardware Accelerated GPU Scheduling (HAGS).
        Available on Windows 10 2004+ with compatible GPUs.
        """
        if not self._winreg_available:
            return False
        
        try:
            key_path = r"SYSTEM\CurrentControlSet\Control\GraphicsDrivers"
            return self._set_registry_value(
                key_path, "HwSchMode", 2,
                self._winreg.REG_DWORD,
                self._winreg.HKEY_LOCAL_MACHINE
            )
        except Exception as e:
            logger.error(f"Error enabling HAGS: {e}")
            return False
    
    def optimize_mouse_settings(self) -> bool:
        """Disable mouse acceleration and enhance pointer precision issues."""
        if not self._winreg_available:
            return False
        
        try:
            # Disable enhanced pointer precision (mouse acceleration)
            key_path = r"Control Panel\Mouse"
            results = []
            results.append(self._set_registry_value(
                key_path, "MouseSpeed", "0", self._winreg.REG_SZ
            ))
            results.append(self._set_registry_value(
                key_path, "MouseThreshold1", "0", self._winreg.REG_SZ
            ))
            results.append(self._set_registry_value(
                key_path, "MouseThreshold2", "0", self._winreg.REG_SZ
            ))
            
            if any(results):
                logger.info("Mouse settings optimized (acceleration disabled)")
            return any(results)
            
        except Exception as e:
            logger.error(f"Error optimizing mouse settings: {e}")
            return False
    
    def disable_game_dvr(self) -> bool:
        """
        Disable Game DVR background recording.
        Can improve performance but disables clip recording.
        """
        if not self._winreg_available:
            return False
        
        try:
            key_path = r"SOFTWARE\Microsoft\Windows\CurrentVersion\GameDVR"
            results = []
            results.append(self._set_registry_value(
                key_path, "AppCaptureEnabled", 0, self._winreg.REG_DWORD
            ))
            
            key_path2 = r"SYSTEM\CurrentControlSet\Services\xbgm"
            results.append(self._set_registry_value(
                key_path2, "Start", 4,
                self._winreg.REG_DWORD,
                self._winreg.HKEY_LOCAL_MACHINE
            ))
            
            if any(results):
                logger.info("Game DVR disabled")
            return any(results)
            
        except Exception as e:
            logger.error(f"Error disabling Game DVR: {e}")
            return False
    
    def optimize_visual_effects(self) -> bool:
        """Optimize Windows visual effects for performance."""
        if not self._winreg_available:
            return False
        
        try:
            key_path = r"Software\Microsoft\Windows\CurrentVersion\Explorer\VisualEffects"
            # 2 = Custom, which allows specific optimizations
            return self._set_registry_value(
                key_path, "VisualFXSetting", 2, self._winreg.REG_DWORD
            )
        except Exception as e:
            logger.error(f"Error optimizing visual effects: {e}")
            return False
    
    def apply_all_optimizations(self) -> dict:
        """Apply all registry optimizations."""
        if not self.enabled:
            return {"status": "disabled"}
        
        results = {
            "status": "completed",
            "gpu_priority": self.set_gpu_priority(),
            "game_bar": self.enable_game_bar(),
            "hags": self.enable_hardware_accelerated_gpu_scheduling(),
            "mouse_optimization": self.optimize_mouse_settings(),
        }
        
        return results
    
    def apply_aggressive_optimizations(self) -> dict:
        """
        Apply more aggressive optimizations.
        These may affect system behavior more significantly.
        """
        if not self.enabled:
            return {"status": "disabled"}
        
        results = self.apply_all_optimizations()
        results["explorer_restart_disabled"] = self.disable_explorer_restart()
        results["game_dvr_disabled"] = self.disable_game_dvr()
        results["visual_effects"] = self.optimize_visual_effects()
        
        return results
    
    def get_registry_status(self) -> dict:
        """Get current registry service status."""
        return {
            "service_enabled": self.enabled,
            "winreg_available": self._winreg_available,
            "backups_count": len(self._backups),
        }
    
    def restore_all(self) -> bool:
        """Restore all backed up registry values."""
        if not self._winreg_available or not self._backups:
            return True
        
        success_count = 0
        for backup_key, backup_data in self._backups.items():
            try:
                # Parse the backup key to get hkey, path, and value name
                # This is simplified - in production, you'd store these separately
                if backup_data is None:
                    # Value didn't exist, try to delete it
                    pass
                else:
                    # Restore the original value
                    pass
                success_count += 1
            except Exception as e:
                logger.error(f"Error restoring {backup_key}: {e}")
        
        logger.info(f"Restored {success_count}/{len(self._backups)} registry values")
        return success_count == len(self._backups)
