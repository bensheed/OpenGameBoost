"""
Power Service
Manages power settings for optimal gaming performance.
"""
import subprocess
import logging
from typing import Optional, Dict, Tuple

logger = logging.getLogger(__name__)


class PowerService:
    """Service to optimize power settings for gaming."""
    
    # Power plan GUIDs
    POWER_PLANS = {
        "balanced": "381b4222-f694-41f0-9685-ff5bb260df2e",
        "high_performance": "8c5e7fda-e8bf-4a96-9a85-a6e23a8c635c",
        "power_saver": "a1841308-3541-4fab-bc81-f71556f20b4a",
        "ultimate_performance": "e9a42b02-d5df-448d-aa00-03f14749eb61",
    }
    
    def __init__(self):
        self.enabled = True
        self.auto_switch = True  # Auto switch to high performance when gaming
        self.original_plan: Optional[str] = None
        self.is_desktop: Optional[bool] = None
        
        # Detect system type
        self._detect_system_type()
    
    def _detect_system_type(self):
        """Detect if the system is a desktop or laptop using WMI."""
        try:
            result = subprocess.run(
                ['powershell', '-Command', 
                 "Get-WmiObject -Class Win32_SystemEnclosure | Select-Object -ExpandProperty ChassisTypes"],
                capture_output=True,
                text=True,
                timeout=10
            )
            
            if result.returncode == 0:
                chassis_types = result.stdout.strip().split('\n')
                # Chassis types: 3,4,5,6,7,15,16 are desktops
                # 8,9,10,11,12,14,18,21 are laptops/portables
                desktop_types = {'3', '4', '5', '6', '7', '15', '16'}
                
                for chassis in chassis_types:
                    chassis = chassis.strip()
                    if chassis in desktop_types:
                        self.is_desktop = True
                        logger.info("System detected as desktop")
                        return
                
                self.is_desktop = False
                logger.info("System detected as laptop/portable")
                
        except Exception as e:
            logger.warning(f"Could not detect system type: {e}")
            self.is_desktop = None
    
    def _run_powercfg(self, args: str) -> Tuple[bool, str]:
        """Run a powercfg command."""
        try:
            result = subprocess.run(
                f"powercfg {args}",
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
    
    def get_current_plan(self) -> Optional[str]:
        """Get the currently active power plan GUID."""
        try:
            success, output = self._run_powercfg("/getactivescheme")
            if success and "GUID" in output:
                # Extract GUID from output like "Power Scheme GUID: xxx-xxx"
                parts = output.split(":")
                if len(parts) >= 2:
                    guid_part = parts[1].strip().split()[0]
                    return guid_part
        except Exception as e:
            logger.error(f"Error getting current power plan: {e}")
        return None
    
    def get_current_plan_name(self) -> str:
        """Get the name of the currently active power plan."""
        current_guid = self.get_current_plan()
        if current_guid:
            for name, guid in self.POWER_PLANS.items():
                if guid.lower() == current_guid.lower():
                    return name.replace("_", " ").title()
        return "Unknown"
    
    def set_power_plan(self, plan_name: str) -> bool:
        """Set the active power plan by name."""
        plan_guid = self.POWER_PLANS.get(plan_name.lower().replace(" ", "_"))
        if not plan_guid:
            logger.error(f"Unknown power plan: {plan_name}")
            return False
        
        success, output = self._run_powercfg(f"/setactive {plan_guid}")
        if success:
            logger.info(f"Power plan set to: {plan_name}")
        else:
            logger.error(f"Failed to set power plan: {output}")
        return success
    
    def set_high_performance(self) -> bool:
        """Set power plan to High Performance."""
        # Save current plan for restoration
        if self.original_plan is None:
            self.original_plan = self.get_current_plan()
        
        # Try Ultimate Performance first (Windows 10 1803+)
        success, _ = self._run_powercfg(f"/setactive {self.POWER_PLANS['ultimate_performance']}")
        if success:
            logger.info("Power plan set to Ultimate Performance")
            return True
        
        # Fall back to High Performance
        return self.set_power_plan("high_performance")
    
    def restore_power_plan(self) -> bool:
        """Restore the original power plan."""
        if self.original_plan:
            success, output = self._run_powercfg(f"/setactive {self.original_plan}")
            if success:
                logger.info("Power plan restored to original")
                self.original_plan = None
            return success
        return True
    
    def create_ultimate_performance_plan(self) -> bool:
        """Create the Ultimate Performance power plan if it doesn't exist."""
        # Check if it exists
        success, output = self._run_powercfg("/list")
        if self.POWER_PLANS['ultimate_performance'] in output.lower():
            return True
        
        # Try to duplicate from High Performance
        success, output = self._run_powercfg(
            f'/duplicatescheme {self.POWER_PLANS["high_performance"]} '
            f'{self.POWER_PLANS["ultimate_performance"]}'
        )
        
        if success:
            # Rename it
            self._run_powercfg(
                f'/changename {self.POWER_PLANS["ultimate_performance"]} '
                f'"Ultimate Performance" "Maximum performance power plan"'
            )
            logger.info("Ultimate Performance plan created")
            return True
        
        return False
    
    def optimize_power_settings(self) -> dict:
        """Apply gaming power optimizations based on system type."""
        if not self.enabled:
            return {"status": "disabled"}
        
        results = {
            "status": "completed",
            "system_type": "desktop" if self.is_desktop else "laptop" if self.is_desktop is False else "unknown",
            "plan_changed": False,
            "previous_plan": self.get_current_plan_name(),
        }
        
        # Save current plan
        self.original_plan = self.get_current_plan()
        
        if self.is_desktop:
            # Desktop: Set to High/Ultimate Performance
            results["plan_changed"] = self.set_high_performance()
            results["new_plan"] = self.get_current_plan_name()
        else:
            # Laptop: Be more conservative, use High Performance but not Ultimate
            results["plan_changed"] = self.set_power_plan("high_performance")
            results["new_plan"] = self.get_current_plan_name()
            
            # Additional laptop optimizations
            self._optimize_laptop_settings()
        
        return results
    
    def _optimize_laptop_settings(self):
        """Apply additional optimizations for laptops."""
        try:
            # Prevent sleep while gaming (requires game to be detected)
            # Set minimum processor state to 100% on AC power
            self._run_powercfg("/setacvalueindex scheme_current sub_processor PROCTHROTTLEMIN 100")
            self._run_powercfg("/setactive scheme_current")
            logger.info("Laptop power settings optimized")
        except Exception as e:
            logger.warning(f"Could not optimize laptop settings: {e}")
    
    def disable_usb_suspend(self) -> bool:
        """Disable USB selective suspend to prevent device disconnections."""
        try:
            success, _ = self._run_powercfg(
                "/setacvalueindex scheme_current 2a737441-1930-4402-8d77-b2bebba308a3 "
                "48e6b7a6-50f5-4782-a5d4-53bb8f07e226 0"
            )
            if success:
                self._run_powercfg("/setactive scheme_current")
                logger.info("USB selective suspend disabled")
            return success
        except Exception as e:
            logger.error(f"Error disabling USB suspend: {e}")
            return False
    
    def disable_pci_power_management(self) -> bool:
        """Disable PCI Express power management for better GPU performance."""
        try:
            success, _ = self._run_powercfg(
                "/setacvalueindex scheme_current 501a4d13-42af-4429-9fd1-a8218c268e20 "
                "ee12f906-d277-404b-b6da-e5fa1a576df5 0"
            )
            if success:
                self._run_powercfg("/setactive scheme_current")
                logger.info("PCI Express power management disabled")
            return success
        except Exception as e:
            logger.error(f"Error disabling PCI power management: {e}")
            return False
    
    def get_power_status(self) -> dict:
        """Get current power configuration status."""
        return {
            "service_enabled": self.enabled,
            "auto_switch": self.auto_switch,
            "current_plan": self.get_current_plan_name(),
            "system_type": "desktop" if self.is_desktop else "laptop" if self.is_desktop is False else "unknown",
            "original_plan_saved": self.original_plan is not None,
        }
    
    def list_power_plans(self) -> list:
        """List all available power plans."""
        plans = []
        success, output = self._run_powercfg("/list")
        if success:
            for line in output.split('\n'):
                if "GUID" in line:
                    plans.append(line.strip())
        return plans
