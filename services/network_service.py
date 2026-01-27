"""
Network Service
Optimizes network settings for gaming by disabling unnecessary protocols.
"""
import subprocess
import logging
from typing import Optional, Dict

logger = logging.getLogger(__name__)


class NetworkService:
    """Service to optimize network settings for gaming."""
    
    def __init__(self):
        self.enabled = True
        self.disable_nagle = True
        self.disable_netbios = True
        self.optimize_dns = True
        self._settings_backup: Dict[str, any] = {}
        
        # Try to import Windows-specific modules
        self._winreg_available = False
        try:
            import winreg
            self._winreg = winreg
            self._winreg_available = True
        except ImportError:
            logger.warning("winreg not available - registry modifications disabled")
    
    def _run_netsh(self, command: str) -> tuple:
        """Run a netsh command and return (success, output)."""
        try:
            result = subprocess.run(
                f"netsh {command}",
                shell=True,
                capture_output=True,
                text=True,
                timeout=30
            )
            return (result.returncode == 0, result.stdout + result.stderr)
        except subprocess.TimeoutExpired:
            return (False, "Command timed out")
        except Exception as e:
            return (False, str(e))
    
    def disable_multicast(self) -> bool:
        """Disable multicast/mDNS which can cause latency spikes."""
        if not self._winreg_available:
            return False
        
        try:
            # Disable LLMNR (Link-Local Multicast Name Resolution)
            key_path = r"SOFTWARE\Policies\Microsoft\Windows NT\DNSClient"
            try:
                key = self._winreg.CreateKeyEx(
                    self._winreg.HKEY_LOCAL_MACHINE,
                    key_path,
                    0,
                    self._winreg.KEY_SET_VALUE | self._winreg.KEY_WOW64_64KEY
                )
                self._winreg.SetValueEx(key, "EnableMulticast", 0, self._winreg.REG_DWORD, 0)
                self._winreg.CloseKey(key)
                logger.info("Multicast/LLMNR disabled")
                return True
            except PermissionError:
                logger.warning("Need admin rights to disable multicast")
                return False
        except Exception as e:
            logger.error(f"Error disabling multicast: {e}")
            return False
    
    def enable_multicast(self) -> bool:
        """Re-enable multicast."""
        if not self._winreg_available:
            return False
        
        try:
            key_path = r"SOFTWARE\Policies\Microsoft\Windows NT\DNSClient"
            try:
                key = self._winreg.OpenKeyEx(
                    self._winreg.HKEY_LOCAL_MACHINE,
                    key_path,
                    0,
                    self._winreg.KEY_SET_VALUE | self._winreg.KEY_WOW64_64KEY
                )
                self._winreg.SetValueEx(key, "EnableMulticast", 0, self._winreg.REG_DWORD, 1)
                self._winreg.CloseKey(key)
                logger.info("Multicast/LLMNR enabled")
                return True
            except FileNotFoundError:
                return True  # Key doesn't exist, multicast is already enabled
            except PermissionError:
                logger.warning("Need admin rights to enable multicast")
                return False
        except Exception as e:
            logger.error(f"Error enabling multicast: {e}")
            return False
    
    def disable_netbios_adapter(self) -> bool:
        """Disable NetBIOS over TCP/IP for all adapters."""
        if not self._winreg_available:
            return False
        
        try:
            # NetBIOS settings are per-adapter in registry
            adapters_path = r"SYSTEM\CurrentControlSet\Services\NetBT\Parameters\Interfaces"
            key = self._winreg.OpenKeyEx(
                self._winreg.HKEY_LOCAL_MACHINE,
                adapters_path,
                0,
                self._winreg.KEY_READ | self._winreg.KEY_WOW64_64KEY
            )
            
            i = 0
            while True:
                try:
                    adapter_name = self._winreg.EnumKey(key, i)
                    adapter_path = f"{adapters_path}\\{adapter_name}"
                    
                    try:
                        adapter_key = self._winreg.OpenKeyEx(
                            self._winreg.HKEY_LOCAL_MACHINE,
                            adapter_path,
                            0,
                            self._winreg.KEY_SET_VALUE | self._winreg.KEY_WOW64_64KEY
                        )
                        # 2 = Disable NetBIOS over TCP/IP
                        self._winreg.SetValueEx(
                            adapter_key, "NetbiosOptions", 0, 
                            self._winreg.REG_DWORD, 2
                        )
                        self._winreg.CloseKey(adapter_key)
                    except PermissionError:
                        pass
                    
                    i += 1
                except OSError:
                    break
            
            self._winreg.CloseKey(key)
            logger.info("NetBIOS disabled on network adapters")
            return True
            
        except PermissionError:
            logger.warning("Need admin rights to disable NetBIOS")
            return False
        except Exception as e:
            logger.error(f"Error disabling NetBIOS: {e}")
            return False
    
    def enable_netbios_adapter(self) -> bool:
        """Re-enable NetBIOS over TCP/IP for all adapters."""
        if not self._winreg_available:
            return False
        
        try:
            adapters_path = r"SYSTEM\CurrentControlSet\Services\NetBT\Parameters\Interfaces"
            key = self._winreg.OpenKeyEx(
                self._winreg.HKEY_LOCAL_MACHINE,
                adapters_path,
                0,
                self._winreg.KEY_READ | self._winreg.KEY_WOW64_64KEY
            )
            
            i = 0
            while True:
                try:
                    adapter_name = self._winreg.EnumKey(key, i)
                    adapter_path = f"{adapters_path}\\{adapter_name}"
                    
                    try:
                        adapter_key = self._winreg.OpenKeyEx(
                            self._winreg.HKEY_LOCAL_MACHINE,
                            adapter_path,
                            0,
                            self._winreg.KEY_SET_VALUE | self._winreg.KEY_WOW64_64KEY
                        )
                        # 0 = Default (use DHCP setting)
                        self._winreg.SetValueEx(
                            adapter_key, "NetbiosOptions", 0,
                            self._winreg.REG_DWORD, 0
                        )
                        self._winreg.CloseKey(adapter_key)
                    except PermissionError:
                        pass
                    
                    i += 1
                except OSError:
                    break
            
            self._winreg.CloseKey(key)
            logger.info("NetBIOS enabled on network adapters")
            return True
            
        except Exception as e:
            logger.error(f"Error enabling NetBIOS: {e}")
            return False
    
    def disable_nagle_algorithm(self) -> bool:
        """
        Disable Nagle's algorithm to reduce network latency.
        This sends packets immediately instead of buffering.
        """
        if not self._winreg_available:
            return False
        
        try:
            # Nagle settings per interface
            interfaces_path = r"SYSTEM\CurrentControlSet\Services\Tcpip\Parameters\Interfaces"
            key = self._winreg.OpenKeyEx(
                self._winreg.HKEY_LOCAL_MACHINE,
                interfaces_path,
                0,
                self._winreg.KEY_READ | self._winreg.KEY_WOW64_64KEY
            )
            
            i = 0
            while True:
                try:
                    interface_name = self._winreg.EnumKey(key, i)
                    interface_path = f"{interfaces_path}\\{interface_name}"
                    
                    try:
                        interface_key = self._winreg.OpenKeyEx(
                            self._winreg.HKEY_LOCAL_MACHINE,
                            interface_path,
                            0,
                            self._winreg.KEY_SET_VALUE | self._winreg.KEY_WOW64_64KEY
                        )
                        # TcpAckFrequency=1 and TcpNoDelay=1 disable Nagle
                        self._winreg.SetValueEx(
                            interface_key, "TcpAckFrequency", 0,
                            self._winreg.REG_DWORD, 1
                        )
                        self._winreg.SetValueEx(
                            interface_key, "TcpNoDelay", 0,
                            self._winreg.REG_DWORD, 1
                        )
                        self._winreg.CloseKey(interface_key)
                    except PermissionError:
                        pass
                    
                    i += 1
                except OSError:
                    break
            
            self._winreg.CloseKey(key)
            logger.info("Nagle's algorithm disabled")
            return True
            
        except PermissionError:
            logger.warning("Need admin rights to disable Nagle's algorithm")
            return False
        except Exception as e:
            logger.error(f"Error disabling Nagle's algorithm: {e}")
            return False
    
    def enable_nagle_algorithm(self) -> bool:
        """Re-enable Nagle's algorithm (restore defaults)."""
        if not self._winreg_available:
            return False
        
        try:
            interfaces_path = r"SYSTEM\CurrentControlSet\Services\Tcpip\Parameters\Interfaces"
            key = self._winreg.OpenKeyEx(
                self._winreg.HKEY_LOCAL_MACHINE,
                interfaces_path,
                0,
                self._winreg.KEY_READ | self._winreg.KEY_WOW64_64KEY
            )
            
            i = 0
            while True:
                try:
                    interface_name = self._winreg.EnumKey(key, i)
                    interface_path = f"{interfaces_path}\\{interface_name}"
                    
                    try:
                        interface_key = self._winreg.OpenKeyEx(
                            self._winreg.HKEY_LOCAL_MACHINE,
                            interface_path,
                            0,
                            self._winreg.KEY_SET_VALUE | self._winreg.KEY_WOW64_64KEY
                        )
                        # Delete the custom values to restore defaults
                        try:
                            self._winreg.DeleteValue(interface_key, "TcpAckFrequency")
                        except FileNotFoundError:
                            pass
                        try:
                            self._winreg.DeleteValue(interface_key, "TcpNoDelay")
                        except FileNotFoundError:
                            pass
                        self._winreg.CloseKey(interface_key)
                    except PermissionError:
                        pass
                    
                    i += 1
                except OSError:
                    break
            
            self._winreg.CloseKey(key)
            logger.info("Nagle's algorithm restored to default")
            return True
            
        except Exception as e:
            logger.error(f"Error enabling Nagle's algorithm: {e}")
            return False
    
    def optimize_network(self) -> dict:
        """Apply all network optimizations."""
        if not self.enabled:
            return {"status": "disabled"}
        
        results = {
            "status": "completed",
            "nagle_disabled": False,
            "netbios_disabled": False,
            "multicast_disabled": False,
        }
        
        if self.disable_nagle:
            results["nagle_disabled"] = self.disable_nagle_algorithm()
        
        if self.disable_netbios:
            results["netbios_disabled"] = self.disable_netbios_adapter()
        
        if self.optimize_dns:
            results["multicast_disabled"] = self.disable_multicast()
        
        return results
    
    def restore_network(self) -> dict:
        """Restore all network settings to defaults."""
        results = {
            "nagle_enabled": self.enable_nagle_algorithm(),
            "netbios_enabled": self.enable_netbios_adapter(),
            "multicast_enabled": self.enable_multicast(),
        }
        return results
    
    def get_network_status(self) -> dict:
        """Get current network optimization status."""
        return {
            "service_enabled": self.enabled,
            "nagle_optimization": self.disable_nagle,
            "netbios_optimization": self.disable_netbios,
            "dns_optimization": self.optimize_dns,
        }
