"""
Game Detector Service
Detects running games and manages game mode optimizations.
"""
import threading
import time
from typing import Callable, Optional, List, Dict
import logging

logger = logging.getLogger(__name__)

# Game definitions with process names and display names
# Sources: PCGamingWiki, Steam forums, Nexus Mods, official documentation
# Only includes games mentioned in the original analysis OR verified executables
SUPPORTED_GAMES: Dict[str, List[str]] = {
    # === Games from original malware analysis (13 games) ===
    "Call of Duty": ["cod.exe", "ModernWarfare.exe", "BlackOpsColdWar.exe", "cod.exe"],
    "Fortnite": ["FortniteClient-Win64-Shipping.exe", "FortniteLauncher.exe"],
    "Apex Legends": ["r5apex.exe"],  # Verified: Respawn engine
    "Counter-Strike 2": ["cs2.exe"],  # Verified: Steam/Valve
    "Valheim": ["valheim.exe"],  # Verified: Steam
    "DOTA 2": ["dota2.exe"],  # Verified: Valve
    "League of Legends": ["League of Legends.exe", "LeagueClient.exe"],  # Verified: Riot
    "Overwatch": ["Overwatch.exe"],  # Verified: Blizzard
    "Valorant": ["VALORANT-Win64-Shipping.exe"],  # Verified: Riot/Unreal
    "GTA V": ["GTA5.exe"],  # Verified: Rockstar
    "Red Dead Redemption 2": ["RDR2.exe"],  # Verified: Rockstar
    "Cyberpunk 2077": ["Cyberpunk2077.exe"],  # Verified: CDPR
    "Minecraft": ["javaw.exe", "Minecraft.Windows.exe"],  # Verified: Java Edition & Bedrock
    
    # === Additional verified games (web research) ===
    "Elden Ring": ["eldenring.exe"],  # Verified: PCGamingWiki
    "Baldur's Gate 3": ["bg3.exe", "bg3_dx11.exe"],  # Verified: Nexus Mods
    "Diablo IV": ["Diablo IV.exe"],  # Verified: Blizzard forums
    "Path of Exile": ["PathOfExile_x64.exe", "PathOfExileSteam.exe"],  # Verified: GGG
    "World of Warcraft": ["Wow.exe", "WowClassic.exe"],  # Verified: Blizzard
}


class GameDetectorService:
    """Service to detect running games and trigger optimizations."""
    
    def __init__(self):
        self.enabled = True
        self.auto_optimize = True
        self.check_interval = 5  # seconds
        self.detected_games: List[str] = []
        self.on_game_detected: Optional[Callable[[str], None]] = None
        self.on_game_closed: Optional[Callable[[str], None]] = None
        self._running = False
        self._thread: Optional[threading.Thread] = None
        self._psutil_available = False
        self._win32_available = False
        
        # Try to import platform-specific modules
        try:
            import psutil
            self._psutil = psutil
            self._psutil_available = True
        except ImportError:
            logger.warning("psutil not available - game detection limited")
            
        try:
            import win32gui
            import win32process
            import win32con
            self._win32gui = win32gui
            self._win32process = win32process
            self._win32con = win32con
            self._win32_available = True
        except ImportError:
            logger.warning("pywin32 not available - focus management limited")
    
    def start(self):
        """Start the game detection service."""
        if self._running:
            return
        self._running = True
        self._thread = threading.Thread(target=self._detection_loop, daemon=True)
        self._thread.start()
        logger.info("Game detector service started")
    
    def stop(self):
        """Stop the game detection service."""
        self._running = False
        if self._thread:
            self._thread.join(timeout=2)
        logger.info("Game detector service stopped")
    
    def _detection_loop(self):
        """Main detection loop."""
        while self._running:
            if self.enabled:
                self._check_games()
            time.sleep(self.check_interval)
    
    def _check_games(self):
        """Check for running games."""
        if not self._psutil_available:
            return
            
        current_games = set()
        
        try:
            for proc in self._psutil.process_iter(['name', 'pid']):
                try:
                    proc_name = proc.info['name']
                    if proc_name:
                        for game_name, process_names in SUPPORTED_GAMES.items():
                            if proc_name.lower() in [p.lower() for p in process_names]:
                                current_games.add(game_name)
                                break
                except (self._psutil.NoSuchProcess, self._psutil.AccessDenied):
                    continue
        except Exception as e:
            logger.error(f"Error checking processes: {e}")
            return
        
        # Check for newly detected games
        previous_games = set(self.detected_games)
        for game in current_games - previous_games:
            logger.info(f"Game detected: {game}")
            if self.auto_optimize and self.on_game_detected:
                self.on_game_detected(game)
        
        # Check for closed games
        for game in previous_games - current_games:
            logger.info(f"Game closed: {game}")
            if self.on_game_closed:
                self.on_game_closed(game)
        
        self.detected_games = list(current_games)
    
    def focus_game(self, game_name: str) -> bool:
        """Bring the game window to focus."""
        if not self._win32_available or not self._psutil_available:
            return False
            
        process_names = SUPPORTED_GAMES.get(game_name, [])
        if not process_names:
            return False
        
        try:
            for proc in self._psutil.process_iter(['name', 'pid']):
                try:
                    if proc.info['name'].lower() in [p.lower() for p in process_names]:
                        pid = proc.info['pid']
                        
                        def callback(hwnd, pids):
                            _, found_pid = self._win32process.GetWindowThreadProcessId(hwnd)
                            if found_pid == pid:
                                if self._win32gui.IsWindowVisible(hwnd):
                                    self._win32gui.SetForegroundWindow(hwnd)
                                    return False
                            return True
                        
                        self._win32gui.EnumWindows(callback, pid)
                        return True
                except (self._psutil.NoSuchProcess, self._psutil.AccessDenied):
                    continue
        except Exception as e:
            logger.error(f"Error focusing game: {e}")
        
        return False
    
    def get_running_games(self) -> List[str]:
        """Get list of currently detected games."""
        return self.detected_games.copy()
    
    def is_game_running(self, game_name: str) -> bool:
        """Check if a specific game is running."""
        return game_name in self.detected_games
    
    def get_supported_games(self) -> List[str]:
        """Get list of all supported games."""
        return list(SUPPORTED_GAMES.keys())
