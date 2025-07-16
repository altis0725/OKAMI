"""
Evolution module for OKAMI system
Handles parsing and applying improvements from evolution crew
"""

from .improvement_parser import ImprovementParser
from .improvement_applier import ImprovementApplier

__all__ = ["ImprovementParser", "ImprovementApplier"]