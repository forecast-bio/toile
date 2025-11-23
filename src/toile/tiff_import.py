"""
TIFF import utilities for microscopy data.

This module handles loading TIFF stacks from microscopy recordings,
with special support for OME-TIFF metadata extraction. It parses
spatial, temporal, and experimental metadata from XML annotations
and supports custom filename parsing for batch processing.
"""

##
# Imports

import os
from pathlib import Path
from glob import glob
import warnings
from datetime import datetime
from uuid import UUID
import re

import numpy as np
import skimage.io as skio
import tifffile
import xmltodict

from toile.schema import (
    Movie,
)

from typing import (
    Optional,
    Callable,
    Any,
    TypeAlias,
)

_FilenameParser: TypeAlias = Callable[[str], dict[str, Any]]

from ._common import (
    _Pathable,
    suppress_stderr,
)


##
# Helpers

# Routines for collating OME TIFF metadata

def _collate_frame_metadata( raw: dict[str, Any] ) -> dict[str, Any]:
    """Extract and normalize per-frame metadata from OME-TIFF XML.

    Parses position (x, y, z), timing (t_index, t), and UUID information
    from the raw XML dictionary structure.

    Args:
        raw: Dictionary parsed from OME-TIFF TiffData/Plane XML elements

    Returns:
        Normalized dictionary with standardized keys (position_x/y/z, t_index, t, uuid)
    """

    ret = dict()

    #

    for k, k_new in [
        ('@PositionX', 'position_x'),
        ('@PositionY', 'position_y'),
        ('@PositionZ', 'position_z'),
    ]:
        if k in raw:
            ret[k_new] = float( raw[k] )
    
    if '@TheT' in raw:
        ret['t_index'] = int( raw['@TheT'] )
    
    if '@DeltaT' in raw:
        ret['t'] = float( raw['@DeltaT'] )

    if 'UUID' in raw:
        if '#text' in raw['UUID']:
            try:
                ret['uuid'] = str( UUID( raw['UUID']['#text'] ) )
            except Exception as e:
                print( f'Invalid frame UUID: "{raw['UUID']['#text']}"' )

    #

    return ret

def _collate_metadata( raw: dict[str, Any],
        date_format: str = '%Y-%m-%dT%H:%M:%S'
    ) -> dict[str, Any]:
    """Extract and normalize movie-level metadata from OME-TIFF XML.

    Parses acquisition date, physical scales, image dimensions, channel info,
    and per-frame metadata from the full OME XML structure.

    Args:
        raw: Dictionary parsed from complete OME-TIFF XML metadata
        date_format: strptime format string for parsing acquisition dates

    Returns:
        Normalized dictionary with keys including:
            - uuid: Movie UUID
            - date_acquired: Acquisition timestamp
            - scale_x/y/z: Physical pixel sizes in microns
            - size_x/y/z/t: Image dimensions
            - channels: List of channel metadata dictionaries
            - frames: List of per-frame metadata dictionaries
    """

    ret = dict()

    #

    ome = raw['OME']

    if '@UUID' in ome:
        try:
            ret['uuid'] = str( UUID( ome['@UUID'] ) )
        except Exception as e:
            print( f'Invalid frame UUID: "{ome["@UUID"]}"' )

    if 'Image' in ome:
        image = ome['Image']

        if 'AcquisitionDate' in image:
            # TODO Better way of validating
            try:
                ret['date_acquired'] = (
                    datetime
                        .strptime( image['AcquisitionDate'], date_format )
                        .strftime( date_format )
                )
            except Exception as e:
                print( f'** Invalid acquisition date: "{image["AcquisitionDate"]}"' )
        
        if 'Pixels' in image:
            pixels = image['Pixels']

            for k, k_new in [
                ('@PhysicalSizeX', 'scale_x'),
                ('@PhysicalSizeY', 'scale_y'),
                ('@PhysicalSizeZ', 'scale_z'),
            ]:
                if k in pixels:
                    ret[k_new] = float( pixels[k] )
                    # TODO Determine
                    ret['scale_unit'] = 'um'
            
            # TODO Determine
            ret['t_unit'] = 's'

            for k, k_new in [
                ('@SizeX', 'size_x'),
                ('@SizeY', 'size_y'),
                ('@SizeZ', 'size_z'),
                ('@SizeT', 'size_t'),
            ]:
                if k in pixels:
                    ret[k_new] = int( pixels[k] )
            
            #

            if 'Channel' in pixels:
                channel = pixels['Channel']

                # TODO Check metadata structure for multi-channel recordings
                if 'channels' not in ret:
                    ret['channels'] = []
                
                new_channel = dict()
                if '@Name' in channel:
                    new_channel['name'] = channel['@Name']
                
                ret['channels'].append( new_channel )
            
            #

            if 'TiffData' in pixels and 'Plane' in pixels:
                frame_iterator = map(
                    lambda x: dict( **x[0], **x[1] ),
                    zip( pixels['TiffData'], pixels['Plane'] )
                )
            elif 'TiffData' in pixels:
                frame_iterator = map(
                    lambda x: dict( **x ),
                    pixels['TiffData']
                )
            elif 'Plane' in pixels:
                frame_iterator = map(
                    lambda x: dict( **x ),
                    pixels['Plane']
                )
            else:
                frame_iterator = None

            if frame_iterator is not None:
                ret['frames'] = []
                for frame_data in frame_iterator:
                    ret['frames'].append( _collate_frame_metadata( frame_data ) )

    #

    return ret

def _unformat( string, pattern ):
    """Reverse of string formatting - extract values from a formatted string.

    Given a string and a format pattern with {placeholders}, extracts the
    values that were used to create the string.

    Args:
        string: The formatted string to parse
        pattern: Format pattern with {key} placeholders (e.g., "mouse_{mouse_id}_slice_{slice_id}.tif")

    Returns:
        Dictionary mapping placeholder names to extracted values

    Example:
        >>> _unformat("mouse_123_slice_A5.tif", "mouse_{mouse_id}_slice_{slice_id}.tif")
        {'mouse_id': '123', 'slice_id': 'A5'}
    """
    regex = re.sub( r'{(.+?)}', r'(?P<_\1>.+)', pattern )
    search_res = re.search( regex, string )
    assert search_res is not None
    values = list( search_res.groups() )
    keys = re.findall(r'{(.+?)}', pattern)
    _dict = dict(zip(keys, values))
    return _dict

_filename_parser_transforms = {
    'identity': lambda d, k, x: dict( **d, **{ k: x } ),
    'float': lambda d, k, x: dict( **d, **{ k: float( x ) } ),
    'int': lambda d, k, x: dict( **d, **{ k: int( x ) } ),
    'split_age_sex': lambda d, k, x: (
        dict( **d,
            **{
                k.split( '_' )[0]: int( x[:-1] ),
                k.split( '_' )[1]: x[-1],
            }
        )
    ),
    'date_compact': lambda d, k, x: dict( **d, **{ k: datetime.strptime( x, '%Y%m%d' ).isoformat() } ),
}

def _make_filename_parser( template: str, transforms: dict[str, str] ) -> _FilenameParser:
    """Create a custom filename parser from a template and transforms.

    Builds a function that extracts structured metadata from filenames
    using a format template and type conversions.

    Args:
        template: Format pattern with {key} placeholders (e.g., "{date}_{mouse_id}_{slice_id}.tif")
        transforms: Dictionary mapping placeholder names to transform functions
            Available transforms: 'identity', 'float', 'int', 'split_age_sex', 'date_compact'

    Returns:
        A parser function that takes a filename string and returns a metadata dictionary

    Example:
        >>> parser = _make_filename_parser(
        ...     "mouse_{mouse_id}_age_{age}.tif",
        ...     {"mouse_id": "int", "age": "int"}
        ... )
        >>> parser("mouse_42_age_120.tif")
        {'_source_filename': 'mouse_42_age_120.tif', 'mouse_id': 42, 'age': 120}
    """
    ##
    def _ret( x: str ) -> dict[str, Any]:
        vals_raw = _unformat( x, template )

        vals = dict()
        vals['_source_filename'] = x
        for k, cur_transform in transforms.items():
            if k not in vals_raw:
                continue
            cur_v = vals_raw[k]
            vals = _filename_parser_transforms[cur_transform](vals, k, cur_v )
        
        return vals
    
    return _ret


##
# Main routine

def load_tiff( path: _Pathable,
        frame_pattern_full: str = '*_*0001.ome.tif*',
        frame_pattern: str = '*.ome.tif*',
        filename_parser: Optional[_FilenameParser] = None,
        #
        to_uint8: bool = False,
    ) -> Movie:
    """Load a TIFF stack from a directory with OME-TIFF metadata extraction.

    Searches for TIFF files matching the specified patterns, loads the image
    stack, and extracts all available metadata from OME-TIFF XML annotations.
    Supports optional filename parsing for batch processing and uint8 normalization
    for ML pipelines.

    Args:
        path: Directory path containing TIFF files
        frame_pattern_full: Glob pattern for full stack files (default: first frame pattern)
        frame_pattern: Fallback glob pattern for TIFF files
        filename_parser: Optional function to extract metadata from filenames
            If None, only filename is stored in metadata
        to_uint8: If True, normalize stack to uint8 (0-255) based on stack-wide max value

    Returns:
        Movie object containing:
            - frames: 3D numpy array (time, height, width)
            - metadata: Combined filename and OME-TIFF metadata
            - frame_metadata: List of per-frame metadata dictionaries

    Raises:
        RuntimeError: If no matching TIFF files found or unsupported multi-channel format

    Example:
        >>> movie = load_tiff("/path/to/recording/")
        >>> movie.frames.shape
        (900, 512, 512)
        >>> movie.metadata['date_acquired']
        '2024-01-15T14:30:00'
    """

    # Normalize args
    path = Path( path )

    if filename_parser is None:
    #     # TODO More general default behavior
        filename_parser = lambda x: dict( filename = x )
        # filename_parser = _parse_filename_1

    #

    # Try full-stack load
    raw_input_full = glob( frame_pattern_full, root_dir = path )
    first_frame_path = None

    # try:

    #
    if len( raw_input_full ) == 1:
        first_frame_path = path / raw_input_full[0]
        
    elif len( raw_input_full ) > 1:

        if all( 'Ch' in x.split( '_' )[-2]
                for x in raw_input_full ):
            first_frame_path = path / raw_input_full[0]

        else:
            raise RuntimeError( f'Unsupported multi-channel format in {path.as_posix()}' )
    
    else:
        raise RuntimeError( f'No matching image stack for {(path / frame_pattern_full).as_posix()}' )

    #

    assert first_frame_path is not None

    #

    # We suppress stderr to hopefully avoid scikit-image's nonsense
    with suppress_stderr():

        first_frame_filename = first_frame_path.name
        # print( first_frame_filename )
        # print( os.path.split( first_frame_filename ) )
        filename_metadata = filename_parser( os.path.split( first_frame_filename )[1] )
        # from pprint import pprint
        # pprint( filename_metadata )
        stack = skio.imread( first_frame_path )
    
    # except Exception as e:
    #     print( f'Issue with:' )
    #     print( raw_input_full )
    #     # Re-raise
    #     raise e

    #

    if to_uint8:
        # Perform stack-wide image normalization
        max_value = np.max( stack )
        tmp = (255. / max_value) * stack.astype( float )
        tmp = np.floor( tmp )
        stack = tmp.astype( np.uint8 )

    #

    # filename_metadata = filename_parser( os.path.split( path )[1] )

    with warnings.catch_warnings():
        warnings.simplefilter( 'ignore' )

        with tifffile.TiffFile( first_frame_path ) as tif:
            if tif.ome_metadata is not None:
                image_metadata = _collate_metadata( xmltodict.parse( tif.ome_metadata ) )
            else:
                image_metadata = dict()
    
    frame_metadata = image_metadata.get( 'frames', None )
    del image_metadata['frames']

    movie_metadata = dict(
        **filename_metadata,
        **image_metadata,
    )

    #

    return Movie(
        frames = stack,
        metadata = movie_metadata,
        frame_metadata = frame_metadata,
    )


#