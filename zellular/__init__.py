"""Zellular SDK for interacting with the Zellular sequencer network.

This package provides a client for sending and fetching batches of transactions
through the Zellular network, with support for different network backends.
"""

# Re-export main classes for better IDE support and discoverability
from .zellular import Zellular as Zellular
from .networks.static import StaticNetwork as StaticNetwork
from .networks.eigenlayer import EigenlayerNetwork as EigenlayerNetwork

# Version information - read from installed package metadata
try:
    from importlib.metadata import version
    __version__ = version("zellular")
except:
    __version__ = "unknown"
