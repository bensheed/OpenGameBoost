# OpenGameBoost Services
from .game_detector import GameDetectorService
from .memory_service import MemoryService
from .network_service import NetworkService
from .power_service import PowerService
from .registry_service import RegistryService
from .suspend_service import SuspendService

__all__ = [
    'GameDetectorService',
    'MemoryService', 
    'NetworkService',
    'PowerService',
    'RegistryService',
    'SuspendService',
]
