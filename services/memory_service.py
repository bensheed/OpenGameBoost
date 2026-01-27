"""
Memory Service
Manages memory optimization by flushing unused memory from processes.
"""
import logging
from typing import Optional, List, Tuple

logger = logging.getLogger(__name__)


class MemoryService:
    """Service to optimize system memory usage."""
    
    def __init__(self):
        self.enabled = True
        self.auto_optimize = True  # Auto-optimize when games detected
        self.exclude_processes: List[str] = []  # Processes to exclude from optimization
        self._psutil_available = False
        self._ctypes_available = False
        self._kernel32 = None
        self._psapi = None
        
        # Try to import required modules
        try:
            import psutil
            self._psutil = psutil
            self._psutil_available = True
        except ImportError:
            logger.warning("psutil not available - memory stats limited")
        
        try:
            import ctypes
            from ctypes import wintypes
            self._ctypes = ctypes
            self._wintypes = wintypes
            self._ctypes_available = True
            
            # Load Windows APIs
            self._kernel32 = ctypes.windll.kernel32
            self._psapi = ctypes.windll.psapi
            
            # Define constants
            self.PROCESS_QUERY_INFORMATION = 0x0400
            self.PROCESS_SET_QUOTA = 0x0100
        except Exception as e:
            logger.warning(f"ctypes/Windows API not available: {e}")
    
    def get_memory_info(self) -> dict:
        """Get current memory usage information."""
        if not self._psutil_available:
            return {"error": "psutil not available"}
        
        try:
            mem = self._psutil.virtual_memory()
            return {
                "total": mem.total,
                "available": mem.available,
                "used": mem.used,
                "percent": mem.percent,
                "total_gb": round(mem.total / (1024**3), 2),
                "available_gb": round(mem.available / (1024**3), 2),
                "used_gb": round(mem.used / (1024**3), 2),
            }
        except Exception as e:
            logger.error(f"Error getting memory info: {e}")
            return {"error": str(e)}
    
    def empty_working_set(self, pid: int) -> bool:
        """
        Empty the working set of a process using PSAPI EmptyWorkingSet.
        This flushes unused memory pages to disk.
        """
        if not self._ctypes_available or not self._kernel32 or not self._psapi:
            return False
        
        try:
            # Open the process with required permissions
            handle = self._kernel32.OpenProcess(
                self.PROCESS_QUERY_INFORMATION | self.PROCESS_SET_QUOTA,
                False,
                pid
            )
            
            if not handle:
                return False
            
            try:
                # Call EmptyWorkingSet
                result = self._psapi.EmptyWorkingSet(handle)
                return bool(result)
            finally:
                self._kernel32.CloseHandle(handle)
                
        except Exception as e:
            logger.error(f"Error emptying working set for PID {pid}: {e}")
            return False
    
    def optimize_all_processes(self, exclude_current: bool = True) -> Tuple[int, int]:
        """
        Optimize memory for all processes by emptying their working sets.
        Returns (success_count, fail_count).
        """
        if not self._psutil_available:
            return (0, 0)
        
        success_count = 0
        fail_count = 0
        current_pid = self._psutil.Process().pid if exclude_current else None
        
        try:
            for proc in self._psutil.process_iter(['pid', 'name']):
                try:
                    pid = proc.info['pid']
                    name = proc.info['name']
                    
                    # Skip current process and system processes
                    if pid == current_pid or pid <= 4:
                        continue
                    
                    # Skip excluded processes
                    if name and name.lower() in [p.lower() for p in self.exclude_processes]:
                        continue
                    
                    if self.empty_working_set(pid):
                        success_count += 1
                    else:
                        fail_count += 1
                        
                except (self._psutil.NoSuchProcess, self._psutil.AccessDenied):
                    fail_count += 1
                    
        except Exception as e:
            logger.error(f"Error during memory optimization: {e}")
        
        logger.info(f"Memory optimization: {success_count} succeeded, {fail_count} failed")
        return (success_count, fail_count)
    
    def optimize_memory(self) -> dict:
        """
        Perform full memory optimization and return results.
        """
        if not self.enabled:
            return {"status": "disabled"}
        
        before = self.get_memory_info()
        success, failed = self.optimize_all_processes()
        after = self.get_memory_info()
        
        freed_mb = 0
        if "available" in before and "available" in after:
            freed_mb = round((after["available"] - before["available"]) / (1024**2), 2)
        
        return {
            "status": "completed",
            "processes_optimized": success,
            "processes_failed": failed,
            "memory_before_percent": before.get("percent", 0),
            "memory_after_percent": after.get("percent", 0),
            "freed_mb": max(0, freed_mb),  # Only show if positive
        }
    
    def set_excluded_processes(self, processes: List[str]):
        """Set list of processes to exclude from optimization."""
        self.exclude_processes = processes
    
    def get_top_memory_processes(self, limit: int = 10) -> List[dict]:
        """Get top memory-consuming processes."""
        if not self._psutil_available:
            return []
        
        processes = []
        try:
            for proc in self._psutil.process_iter(['pid', 'name', 'memory_info']):
                try:
                    mem_info = proc.info.get('memory_info')
                    if mem_info:
                        processes.append({
                            'pid': proc.info['pid'],
                            'name': proc.info['name'],
                            'memory_mb': round(mem_info.rss / (1024**2), 2)
                        })
                except (self._psutil.NoSuchProcess, self._psutil.AccessDenied):
                    continue
        except Exception as e:
            logger.error(f"Error getting top processes: {e}")
        
        # Sort by memory usage
        processes.sort(key=lambda x: x['memory_mb'], reverse=True)
        return processes[:limit]
