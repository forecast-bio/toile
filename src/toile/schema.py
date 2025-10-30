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
from numpy.typing import (
    NDArray,
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

Identifier: TypeAlias = int | str

## NEW

@dataclass
class SliceRecordingFrame( atdata.PackableSample ):
    """TODO"""

    ##

    # Required
    data: NDArray
    """`numpy` array containing the frame's image data"""
    
    mouse_id: Identifier
    """TODO"""
    slice_id: Identifier
    """TODO"""

@dataclass
class ImageSample( atdata.PackableSample ):
    """TODO"""
    data: NDArray

@atdata.lens
def project_image( source: SliceRecordingFrame ) -> ImageSample:
    return ImageSample(
        data = source.data
    )
@project_image.putter
def put_image( view: ImageSample, source: SliceRecordingFrame ) -> SliceRecordingFrame:
    return SliceRecordingFrame(
        data = view.data,
        mouse_id = source.mouse_id,
        slice_id = source.slice_id
    )

## OLD

@dataclass
class Position3:
    """TODO"""
    ##

    # Required
    x: float
    """The $x$-position"""
    y: float
    """The $y$-position"""
    z: float
    """The $z$-position"""

    # Optional
    unit: PositionUnit | None = None
    """Unit for interpreting coordinate vlaues"""

# Metadata

@dataclass
class MovieFrameMetadata:
    """TODO"""
    ##

    # Required
    t_index: int
    """Sequential index of this frame within the larger recording"""

    # Optional
    position: Position3 | None = None
    """The offset position of the stage at this time in the recording"""
    t: float | None = None
    """Acquisition time of this frame (in s)"""
    uuid: str | None = None
    """UUID given to frame at acquisition"""

@dataclass
class MovieMetadata:
    """TODO"""

    ##

    # Required
    # ...

    # Optional
    filename: str | None = None
    """Original source filename of raw movie"""
    date_saved: str | None = None
    """Timestamp for when the original full movie file was saved"""

@dataclass
class ChannelMetadata:
    """TODO"""

    ##

    # Required
    # ...

    # Optional
    name: str | None = None
    """Descriptive name of this recording channel"""

@dataclass
class SliceRecordingMetadata:
    """TODO"""

    ##

    # Required
    mouse_id: Identifier
    """TODO"""
    slice_id: Identifier
    """TODO"""

    # Optional
    intervention: Identifier | None = None
    """TODO"""
    condition: Identifier | None = None
    """TODO"""
    replicate_id: Identifier | None = None
    """TODO"""


# Samples

# @atdata.packable
# class SliceRecordingFrame:
#     """TODO"""

#     ##

#     # Required
#     data: NDArray
#     """`numpy` array containing the frame's image data"""

#     session: SliceRecordingMetadata
#     """Metadata about the experimental session"""
#     movie: MovieMetadata
#     """Metadata about the full movie recording"""
#     frame: MovieFrameMetadata
#     """Metadata about this individual frame within the full recording"""

# @dataclass
# class SliceRecordingFrame( atdata.PackableSample ):
#     """TODO"""

#     ##

#     # Required
#     data: NDArray
#     """`numpy` array containing the frame's image data"""
    
#     mouse_id: Identifier
#     """TODO"""
#     slice_id: Identifier
#     """TODO"""


#