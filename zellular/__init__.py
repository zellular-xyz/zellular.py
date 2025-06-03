"""Zellular SDK for interacting with the Zellular sequencer network.

This package provides a client for sending and fetching batches of transactions
through the Zellular network, with support for different network backends.
"""

from .zellular import Zellular as Zellular
from .networks.static import StaticNetwork as StaticNetwork
from .networks.eigenlayer import EigenlayerNetwork as EigenlayerNetwork

try:
    from importlib.metadata import version

    __version__ = version("zellular")
except Exception:
    __version__ = "unknown"
