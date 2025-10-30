"""
Utilities for exporting data
"""

##
# Imports

from typer import Typer

import os
import gzip
from pathlib import (
    Path,
)
from glob import glob

import toile.schema as schema

from tqdm import tqdm
import numpy as np
import webdataset as wds

from typing import (
    TypeAlias,
    Literal,
)


##
# Type shortcuts

Pathable: TypeAlias = Path | str


##
# Common

ExportKind: TypeAlias = Literal[
    'movies',
    'images',
]

def export_tiff(
        input_path: Pathable,
        output_dir: Pathable,
        stem: str = '',
        kind: ExportKind = 'movies',
    ) -> None:
    """TODO"""
    print( 'Will do a thing here!' )

def export_test(
        output_dir: Pathable,
        stem: str = '',
        compressed: bool = False,
        #
        kind: ExportKind = 'images',
        **kwargs
    ) -> None:
    """TODO"""

    image_size = (256, 256)
    image_planes = 900

    if len( stem ) == 0:
        stem = Path( output_dir ).stem
    
    Path( output_dir ).mkdir( parents = True, exist_ok = True )

    # wds_extension = '.tar.gz' if compressed else '.tar'
    wds_extension = '.tar'

    wds_pattern = (
        Path( output_dir )
        / f'{stem}-%06d{wds_extension}'
    ).as_posix()

    if kind == 'images':

        print( 'Exporting images ...' )

        with wds.ShardWriter( pattern = wds_pattern, **kwargs ) as sink:
            for i in tqdm( range( image_planes ) ):
                cur_frame = schema.ImageSample(
                    data = np.random.randint( 32,767, size = image_size )
                )
                sink.write( cur_frame.as_wds )
    
    else:
        raise NotImplementedError()

    if compressed:

        print( 'Compressing outputs ...' )

        shard_glob = (
            Path( output_dir )
            / f'{stem}-*{wds_extension}'
        ).as_posix()

        for p in glob( shard_glob ):
            print( f'    {p}', end = '', flush = True )
            with open( p, 'rb' ) as f_src:
                p_dest = p + '.gz'
                print( f' -> {p_dest} ...', end = '', flush = True )
                with gzip.open( p_dest, 'wb', compresslevel = 4 ) as f_dest:
                    f_dest.write( f_src.read() )
                print( ' Done.' )
            
            os.remove( p )
    
    print( 'Done' )

##
# Typer app

app = Typer()

@app.command( 'test-images' )
def _cli_export_test_images(
            output: str,
            stem: str = '',
            compressed: bool = False,
        ):
    export_test( output, stem,
        compressed = compressed,
        #
        kind = 'images',
    )

@app.command( 'movies' )
def _cli_export_movies(
            input: str,
            output: str,
            stem: str = '',
        ):
    export_tiff( input, output, stem, kind = 'movies' )

@app.command( 'images' )
def _cli_export_images(
            input: str,
            output: str,
            stem: str = '',    
        ):
    export_tiff( input, output, stem, kind = 'images' )


##