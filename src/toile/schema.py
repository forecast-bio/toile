"""
Dataset sample schemas and data structures for astrocyte dynamics.

This module defines the core data structures used throughout toile,
built on the atdata.PackableSample framework for serialization to
WebDataset format. Includes schemas for movies, frames, and experimental
metadata, along with lens transformations for data conversion.
"""

##
# Imports

import atdata

from dataclasses import dataclass

from typing import (
    Any,
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

## Convenience stores for intermediate handling

@dataclass
class Movie( atdata.PackableSample ):
    """Generic movie data extracted from a TIFF stack.

    This is a convenience container for intermediate handling of full
    microscopy recordings before splitting into individual frames.

    Attributes:
        frames: 3D numpy array with shape (time, height, width)
        metadata: Dictionary of movie-level metadata (acquisition settings, etc.)
        frame_metadata: List of per-frame metadata dictionaries (timing, position, etc.)
    """
    frames: NDArray
    metadata: dict[str, Any] | None = None
    frame_metadata: list[dict[str, Any]] | None = None

@dataclass
class Frame( atdata.PackableSample ):
    """Generic image data extracted as a movie frame from a TIFF stack.

    Individual frames are extracted from Movie objects for export to
    WebDataset format.

    Attributes:
        image: 2D numpy array containing the frame's image data
        metadata: Combined movie and frame-level metadata dictionary
    """
    image: NDArray
    metadata: dict[str, Any] | None = None

## NEW

@dataclass
class SliceRecordingFrame( atdata.PackableSample ):
    """Recording frame from a brain slice experiment with experimental identifiers.

    This schema associates image data with experimental session metadata
    for tracking data across mice and slice preparations.

    Attributes:
        data: 2D numpy array containing the frame's image data
        mouse_id: Unique identifier for the mouse subject
        slice_id: Unique identifier for the slice preparation from this mouse
    """

    ##

    # Required
    data: NDArray
    """`numpy` array containing the frame's image data"""

    mouse_id: Identifier
    """Unique identifier for the mouse subject"""
    slice_id: Identifier
    """Unique identifier for the slice preparation from this mouse"""

@dataclass
class ImageSample( atdata.PackableSample ):
    """Simplified image sample containing only pixel data.

    This is a minimal schema for ML pipelines that don't need experimental
    metadata. Can be projected from SliceRecordingFrame using the
    project_image lens.

    Attributes:
        data: 2D numpy array containing the image data
    """
    data: NDArray

@atdata.lens
def project_image( source: SliceRecordingFrame ) -> ImageSample:
    """Project a SliceRecordingFrame to an ImageSample by extracting image data.

    This lens allows data transformations between full experimental frames
    and minimal image samples for ML workflows.

    Args:
        source: Source frame with experimental metadata

    Returns:
        ImageSample containing only the image data
    """
    return ImageSample(
        data = source.data
    )
@project_image.putter
def put_image( view: ImageSample, source: SliceRecordingFrame ) -> SliceRecordingFrame:
    """Reconstruct a SliceRecordingFrame from an ImageSample view.

    This is the inverse lens operation, preserving the original metadata
    while updating the image data.

    Args:
        view: Modified ImageSample with new image data
        source: Original SliceRecordingFrame to preserve metadata from

    Returns:
        SliceRecordingFrame with updated image data and preserved metadata
    """
    return SliceRecordingFrame(
        data = view.data,
        mouse_id = source.mouse_id,
        slice_id = source.slice_id
    )

## OLD

@dataclass
class Position3:
    """3D spatial position with optional units.

    Represents microscope stage position or other spatial coordinates.

    Attributes:
        x: The x-coordinate position
        y: The y-coordinate position
        z: The z-coordinate position
        unit: Unit for interpreting coordinate values (um, mm, or m)
    """
    ##

    # Required
    x: float
    """The x-coordinate position"""
    y: float
    """The y-coordinate position"""
    z: float
    """The z-coordinate position"""

    # Optional
    unit: PositionUnit | None = None
    """Unit for interpreting coordinate values (um, mm, or m)"""

# Metadata

@dataclass
class MovieFrameMetadata:
    """Metadata for a single frame within a microscopy recording.

    Contains timing, position, and identification information extracted
    from OME-TIFF metadata.

    Attributes:
        t_index: Sequential index of this frame within the larger recording
        position: The microscope stage position at this time in the recording
        t: Acquisition time of this frame (in seconds)
        uuid: UUID given to frame at acquisition
    """
    ##

    # Required
    t_index: int
    """Sequential index of this frame within the larger recording"""

    # Optional
    position: Position3 | None = None
    """The microscope stage position at this time in the recording"""
    t: float | None = None
    """Acquisition time of this frame (in seconds)"""
    uuid: str | None = None
    """UUID given to frame at acquisition"""

@dataclass
class MovieMetadata:
    """Metadata for a full microscopy recording.

    Contains file-level information about the recording session.

    Attributes:
        filename: Original source filename of raw movie
        date_saved: Timestamp for when the original full movie file was saved
    """

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
    """Metadata for a single recording channel in multi-channel imaging.

    Attributes:
        name: Descriptive name of this recording channel (e.g., "GCaMP6", "tdTomato")
    """

    ##

    # Required
    # ...

    # Optional
    name: str | None = None
    """Descriptive name of this recording channel (e.g., "GCaMP6", "tdTomato")"""

@dataclass
class SliceRecordingMetadata:
    """Experimental metadata for brain slice recordings.

    Contains identifiers and experimental conditions for tracking data
    across experimental sessions.

    Attributes:
        mouse_id: Unique identifier for the mouse subject
        slice_id: Unique identifier for the slice preparation
        intervention: Identifier for experimental intervention (e.g., drug treatment)
        condition: Identifier for experimental condition (e.g., genotype, treatment group)
        replicate_id: Identifier for experimental replicate
    """

    ##

    # Required
    mouse_id: Identifier
    """Unique identifier for the mouse subject"""
    slice_id: Identifier
    """Unique identifier for the slice preparation"""

    # Optional
    intervention: Identifier | None = None
    """Identifier for experimental intervention (e.g., drug treatment)"""
    condition: Identifier | None = None
    """Identifier for experimental condition (e.g., genotype, treatment group)"""
    replicate_id: Identifier | None = None
    """Identifier for experimental replicate"""


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