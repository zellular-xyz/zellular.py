"""Network implementations for Zellular.

This module provides different network backend implementations:
- StaticNetwork: For fixed, predefined operators (e.g., testing environments)
- EigenlayerNetwork: For operators managed through the EigenLayer protocol
"""

# Re-export base Network class and type definitions
from .base import Network as Network
from .types import Operator as Operator

# Re-export network implementations
from .static import StaticNetwork as StaticNetwork
from .eigenlayer import EigenlayerNetwork as EigenlayerNetwork
