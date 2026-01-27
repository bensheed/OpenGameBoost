"""
Suspend Service
Suspends non-essential processes to free up CPU/RAM for gaming.
This is the CORE functionality shown in the original software demo.
"""
import logging
from typing import List, Dict, Optional, Set
import os

logger = logging.getLogger(__name__)

# Process categories for suspension
BROWSER_PROCESSES = [
    "chrome.exe", "firefox.exe", "msedge.exe", "opera.exe", "brave.exe",
    "vivaldi.exe", "waterfox.exe", "iexplore.exe", "safari.exe",
    # Browser helpers
    "chrome_crashpad_handler.exe", "firefox_crashpad_handler.exe",
]

LAUNCHER_PROCESSES = [
    # Steam
    "steam.exe", "steamwebhelper.exe", "steamservice.exe",
    # Epic Games
    "EpicGamesLauncher.exe", "EpicWebHelper.exe",
    # Battle.net
    "Battle.net.exe", "Agent.exe",
    # EA
    "EADesktop.exe", "EABackgroundService.exe", "Origin.exe",
    # Ubisoft
    "UbisoftConnect.exe", "upc.exe",
    # GOG
    "GalaxyClient.exe", "GalaxyClientService.exe",
    # Xbox
    "XboxPcApp.exe", "XboxPcAppFT.exe",
    # Rockstar
    "Rockstar-Launcher.exe",
    # Riot
    "RiotClientServices.exe",
]

BACKGROUND_PROCESSES = [
    # Communication apps
    "Discord.exe", "Slack.exe", "Teams.exe", "Zoom.exe", "Skype.exe",
    # Media
    "Spotify.exe", "iTunes.exe",
    # Utilities
    "OneDrive.exe", "Dropbox.exe", "GoogleDriveFS.exe",
    # Hardware utilities (optional - be careful)
    "iCUE.exe", "NZXT CAM.exe", "RazerCentral.exe",
]


class SuspendService:
    """
    Service to suspend and resume processes for gaming optimization.
    Uses Windows NtSuspendProcess/NtResumeProcess APIs.
    """
    
    def __init__(self):
        self.enabled = True
        self.suspend_explorer = True
        self.suspend_browsers = True
        self.suspend_launchers = True
        self.suspend_background = False  # Optional, off by default
        
        self._suspended_pids: Set[int] = set()
        self._explorer_pid: Optional[int] = None
        
        # Try to import required modules
        self._psutil_available = False
        self._ctypes_available = False
        
        try:
            import psutil
            self._psutil = psutil
            self._psutil_available = True
        except ImportError:
            logger.warning("psutil not available - suspend service disabled")
        
        try:
            import ctypes
            from ctypes import wintypes
            self._ctypes = ctypes
            self._wintypes = wintypes
            self._ctypes_available = True
            self._setup_windows_apis()
        except Exception as e:
            logger.warning(f"Windows APIs not available: {e}")
    
    def _setup_windows_apis(self):
        """Set up Windows NT API functions for process suspension."""
        try:
            self._ntdll = self._ctypes.windll.ntdll
            self._kernel32 = self._ctypes.windll.kernel32
            
            # Process access rights
            self.PROCESS_SUSPEND_RESUME = 0x0800
            self.PROCESS_QUERY_INFORMATION = 0x0400
            
            # NtSuspendProcess and NtResumeProcess
            self._NtSuspendProcess = self._ntdll.NtSuspendProcess
            self._NtSuspendProcess.argtypes = [self._wintypes.HANDLE]
            self._NtSuspendProcess.restype = self._ctypes.c_long
            
            self._NtResumeProcess = self._ntdll.NtResumeProcess
            self._NtResumeProcess.argtypes = [self._wintypes.HANDLE]
            self._NtResumeProcess.restype = self._ctypes.c_long
            
            logger.info("Windows suspend APIs initialized")
        except Exception as e:
            logger.error(f"Failed to setup Windows APIs: {e}")
            self._ctypes_available = False
    
    def _suspend_process(self, pid: int) -> bool:
        """Suspend a process by PID using NtSuspendProcess."""
        if not self._ctypes_available:
            return False
        
        try:
            handle = self._kernel32.OpenProcess(
                self.PROCESS_SUSPEND_RESUME | self.PROCESS_QUERY_INFORMATION,
                False, pid
            )
            if not handle:
                return False
            
            try:
                result = self._NtSuspendProcess(handle)
                if result == 0:  # STATUS_SUCCESS
                    self._suspended_pids.add(pid)
                    return True
                return False
            finally:
                self._kernel32.CloseHandle(handle)
        except Exception as e:
            logger.error(f"Error suspending PID {pid}: {e}")
            return False
    
    def _resume_process(self, pid: int) -> bool:
        """Resume a suspended process by PID using NtResumeProcess."""
        if not self._ctypes_available:
            return False
        
        try:
            handle = self._kernel32.OpenProcess(
                self.PROCESS_SUSPEND_RESUME | self.PROCESS_QUERY_INFORMATION,
                False, pid
            )
            if not handle:
                return False
            
            try:
                result = self._NtResumeProcess(handle)
                if result == 0:  # STATUS_SUCCESS
                    self._suspended_pids.discard(pid)
                    return True
                return False
            finally:
                self._kernel32.CloseHandle(handle)
        except Exception as e:
            logger.error(f"Error resuming PID {pid}: {e}")
            return False
    
    def _get_pids_by_name(self, process_names: List[str]) -> List[int]:
        """Get all PIDs matching the given process names."""
        if not self._psutil_available:
            return []
        
        pids = []
        names_lower = [n.lower() for n in process_names]
        
        try:
            for proc in self._psutil.process_iter(['pid', 'name']):
                try:
                    if proc.info['name'] and proc.info['name'].lower() in names_lower:
                        pids.append(proc.info['pid'])
                except (self._psutil.NoSuchProcess, self._psutil.AccessDenied):
                    continue
        except Exception as e:
            logger.error(f"Error getting PIDs: {e}")
        
        return pids
    
    def suspend_explorer(self) -> bool:
        """
        Suspend Windows Explorer (explorer.exe).
        WARNING: This will make the taskbar and desktop unresponsive!
        """
        if not self._psutil_available:
            return False
        
        try:
            for proc in self._psutil.process_iter(['pid', 'name']):
                try:
                    if proc.info['name'] and proc.info['name'].lower() == 'explorer.exe':
                        pid = proc.info['pid']
                        if self._suspend_process(pid):
                            self._explorer_pid = pid
                            logger.info(f"Suspended explorer.exe (PID: {pid})")
                            return True
                except (self._psutil.NoSuchProcess, self._psutil.AccessDenied):
                    continue
        except Exception as e:
            logger.error(f"Error suspending explorer: {e}")
        
        return False
    
    def resume_explorer(self) -> bool:
        """Resume Windows Explorer."""
        if self._explorer_pid:
            result = self._resume_process(self._explorer_pid)
            if result:
                logger.info(f"Resumed explorer.exe (PID: {self._explorer_pid})")
                self._explorer_pid = None
            return result
        return True
    
    def suspend_browsers(self) -> Dict[str, int]:
        """Suspend all browser processes."""
        results = {"suspended": 0, "failed": 0}
        
        pids = self._get_pids_by_name(BROWSER_PROCESSES)
        for pid in pids:
            if self._suspend_process(pid):
                results["suspended"] += 1
            else:
                results["failed"] += 1
        
        logger.info(f"Suspended {results['suspended']} browser processes")
        return results
    
    def suspend_launchers(self) -> Dict[str, int]:
        """Suspend all game launcher processes."""
        results = {"suspended": 0, "failed": 0}
        
        pids = self._get_pids_by_name(LAUNCHER_PROCESSES)
        for pid in pids:
            if self._suspend_process(pid):
                results["suspended"] += 1
            else:
                results["failed"] += 1
        
        logger.info(f"Suspended {results['suspended']} launcher processes")
        return results
    
    def suspend_background_apps(self) -> Dict[str, int]:
        """Suspend background applications (Discord, Spotify, etc.)."""
        results = {"suspended": 0, "failed": 0}
        
        pids = self._get_pids_by_name(BACKGROUND_PROCESSES)
        for pid in pids:
            if self._suspend_process(pid):
                results["suspended"] += 1
            else:
                results["failed"] += 1
        
        logger.info(f"Suspended {results['suspended']} background processes")
        return results
    
    def activate_game_mode(self) -> Dict[str, any]:
        """
        Activate Game Mode - suspend all configured process categories.
        This is the main action from the original software.
        """
        if not self.enabled:
            return {"status": "disabled"}
        
        results = {
            "status": "activated",
            "explorer_suspended": False,
            "browsers_suspended": 0,
            "launchers_suspended": 0,
            "background_suspended": 0,
        }
        
        if self.suspend_explorer:
            results["explorer_suspended"] = self.suspend_explorer()
        
        if self.suspend_browsers:
            browser_results = self.suspend_browsers()
            results["browsers_suspended"] = browser_results["suspended"]
        
        if self.suspend_launchers:
            launcher_results = self.suspend_launchers()
            results["launchers_suspended"] = launcher_results["suspended"]
        
        if self.suspend_background:
            bg_results = self.suspend_background_apps()
            results["background_suspended"] = bg_results["suspended"]
        
        total = (
            (1 if results["explorer_suspended"] else 0) +
            results["browsers_suspended"] +
            results["launchers_suspended"] +
            results["background_suspended"]
        )
        results["total_suspended"] = total
        
        logger.info(f"Game Mode activated - {total} processes suspended")
        return results
    
    def deactivate_game_mode(self) -> Dict[str, any]:
        """
        Deactivate Game Mode - resume all suspended processes.
        """
        results = {
            "status": "deactivated",
            "resumed": 0,
            "failed": 0,
        }
        
        # Resume explorer first
        if self._explorer_pid:
            if self.resume_explorer():
                results["resumed"] += 1
            else:
                results["failed"] += 1
        
        # Resume all other suspended processes
        for pid in list(self._suspended_pids):
            if self._resume_process(pid):
                results["resumed"] += 1
            else:
                results["failed"] += 1
        
        logger.info(f"Game Mode deactivated - {results['resumed']} processes resumed")
        return results
    
    def get_suspendable_processes(self) -> Dict[str, List[str]]:
        """Get list of currently running processes that can be suspended."""
        if not self._psutil_available:
            return {}
        
        result = {
            "browsers": [],
            "launchers": [],
            "background": [],
        }
        
        try:
            for proc in self._psutil.process_iter(['name']):
                try:
                    name = proc.info['name']
                    if not name:
                        continue
                    name_lower = name.lower()
                    
                    if name_lower in [p.lower() for p in BROWSER_PROCESSES]:
                        if name not in result["browsers"]:
                            result["browsers"].append(name)
                    elif name_lower in [p.lower() for p in LAUNCHER_PROCESSES]:
                        if name not in result["launchers"]:
                            result["launchers"].append(name)
                    elif name_lower in [p.lower() for p in BACKGROUND_PROCESSES]:
                        if name not in result["background"]:
                            result["background"].append(name)
                except (self._psutil.NoSuchProcess, self._psutil.AccessDenied):
                    continue
        except Exception as e:
            logger.error(f"Error scanning processes: {e}")
        
        return result
    
    def get_status(self) -> Dict[str, any]:
        """Get current suspend service status."""
        return {
            "enabled": self.enabled,
            "game_mode_active": len(self._suspended_pids) > 0 or self._explorer_pid is not None,
            "suspended_count": len(self._suspended_pids) + (1 if self._explorer_pid else 0),
            "explorer_suspended": self._explorer_pid is not None,
            "settings": {
                "suspend_explorer": self.suspend_explorer,
                "suspend_browsers": self.suspend_browsers,
                "suspend_launchers": self.suspend_launchers,
                "suspend_background": self.suspend_background,
            }
        }
