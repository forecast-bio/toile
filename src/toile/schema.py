"""
Dataset sample schemas
"""

##
# Imports

import atdata

from dataclasses import dataclass

from typing import (
    Literal,
    TypeAlias,
)


##
# Sample types

# Helpers

PositionUnit: TypeAlias = Literal[
    'um',
    'mm',
    'm',
]

TimeUnit: TypeAlias = Literal[
    'ms',
    's',
    'min',
    'h'
]

# Metadata

@dataclass
class MovieFrameMetadata:
    """TODO"""
    ##

    # Required
    t_index: int
    """Sequential index of this frame"""

    # Optional
    position_x: float | None
    """x-position of stage offset"""
    position_y: float | None
    """y-position of stage offset"""
    position_z: float | None
    """z-position of stage offset"""
    position_unit: PositionUnit
    """Unit for interpreting `position_*` vlaues"""

    t: float | None
    """Acquisition time of this frame (in s)"""

    uuid: str | None
    """UUID given to frame at acquisition"""

@dataclass
class MovieMetadata:
    """TODO"""

    ##

    # Required

    pass

# Samples

@atdata.packable
class 


