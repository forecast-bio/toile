"""TODO"""

##
# Imports

import os
from pathlib import Path
from glob import glob
import warnings
from datetime import datetime
from uuid import UUID

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

from ._common import (
    _Pathable,
    suppress_stderr,
)


##
# Helpers

# Routines for collating OME TIFF metadata

def _collate_frame_metadata( raw: dict[str, Any] ) -> dict[str, Any]:
    """
    TODO
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
    """
    TODO
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


##
# Main routine

def load_tiff( path: _Pathable,
        frame_pattern_full: str = '*_*0001.ome.tif*',
        frame_pattern: str = '*.ome.tif*',
        filename_parser: Optional[Callable[[str], dict]] = None,
        #
        to_uint8: bool = False,
    ) -> Movie:

    # Normalize args
    path = Path( path )

    if filename_parser is None:
    #     # TODO More general default behavior
        filename_parser = lambda x: dict()
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

    metadata = dict(
        **filename_metadata,
        **image_metadata,
    )

    #

    return Movie(
        frames = stack,
        metadata = metadata,
    )


#