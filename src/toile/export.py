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
import json

import toile.schema as schema

from tqdm import tqdm
import numpy as np
import webdataset as wds

from typing import (
    TypeAlias,
    Literal,
    Optional,
)

from ._common import (
    _Pathable,
)


##
# Type shortcuts

_WDSWriter: TypeAlias = wds.writer.ShardWriter | wds.writer.TarWriter


##
# Helper methods

def _write_movie_frames(
            ds: schema.Movie,
            dest: _WDSWriter,
            key_template: Optional[str] = None,
            i_start: int = 0,
        ) -> int:
    """
    TODO
    """
    ##

    # Normalize args
    if key_template is None:
        key_template = 'sample{i:06d}'

    #

    i_dataset = i_start
    for i_movie, cur_frame_meta in (
        zip(
            range( ds.frames.shape[0] ),
            ds.frame_metadata,
        )
    ):
        cur_metadata = { k: v
                         for k, v in ds.metadata.items() }
        cur_metadata['frame'] = cur_frame_meta

        cur_sample = schema.Frame(
            image = ds.frames[i_movie, :, :],
            metadata = cur_metadata,
        )
        dest_data = cur_sample.as_wds
        dest_data['__key__'] = key_template.format(
            i_dataset = i_dataset,
            i_group = i_movie,
        )

        dest.write( dest_data )
        i_dataset += 1
    
    return i_dataset


##
# Common

ExportKind: TypeAlias = Literal[
    'movies',
    'images',
]

def export_tiff(
        input_path: _Pathable,
        output_dir: _Pathable,
        stem: str = '',
        #
        kind: ExportKind = 'movies',
        to_uint8: bool = False,
        #
        shard_size: float = 38_000_000.,
        compressed: bool = False,
        #
        verbose: bool = False,
        #
        **kwargs
    ) -> None:
    """TODO"""
    ##

    def _printv( *a, **b ):
        if verbose:
            print( *a, **b )

    # Normalize args
    output_dir = Path( output_dir )
    if len( stem ) == 0:
        stem = Path( output_dir ).stem

    # Setup output directory
    output_dir.mkdir( parents = True, exist_ok = True )
    output_pattern = (output_dir / f'{stem}-%06d.tar').as_posix()

    # Parse config
    input_paths: list[_Pathable] = []

    if kind == 'images':
        key_template = 'tseries-{i_dataset}-frame-{i_group}'

    # Start building dataset
    n_succeeded = 0
    n_failed = 0

    with wds.writer.ShardWriter( output_pattern,
        maxsize = shard_size,
    ) as dest:
        
        for i_input, cur_input_path in enumerate( input_paths ):
            cur_input_path = Path( cur_input_path )

            _printv( f'🤔 Working on {cur_input_path} ...' )

            #
            _printv( '    💽 Loading ...', end = '' )

            try:
                cur_ds = load_movie( cur_input_path,
                    to_uint8 = to_uint8,
                    filename_parser = filename_parser,
                )
                _printv( ' Done 🟢' )
            
            except Exception as e:
                _printv( ' Failed 🔴' )
                _printv( 8 * ' ', e )
                if not verbose:
                    print( f'Failed to load movie {cur_input_path}:' )
                    print( 4 * ' ', e )

                n_failed += 1
                continue

            #
            _printv( '    📝 Writing to archive ...', end = '' )

            try:

                if kind == 'movies':
                    raise NotImplementedError()
                    # _write_movie_entire( cur_ds, i_sample, dest )
                    # cur_final = i_sample + 1

                elif kind == 'frames':
                    cur_final = _write_movie_frames( cur_ds, dest,
                        key_template = key_template,
                        # i_start = i_dataset,
                    )

                elif kind == 'clips':
                    raise NotImplementedError()
                
                else:
                    raise ValueError( f'Unrecognized export kind: {kind}' )
                
                _printv( ' Done 🟢' )
            
            except Exception as e:
                _printv( ' Failed 🔴' )
                _printv( 8 * ' ', e )
                if not verbose:
                    print( f'Failed to export movie {cur_input_path}:' )
                    print( 4 * ' ', e )

                n_failed += 1
                continue

            #
        
            _printv( '    ✅ Done.' )
            n_succeeded += 1

##

def export_test(
        output_dir: _Pathable,
        stem: str = '',
        #
        kind: ExportKind = 'images',
        #
        compressed: bool = False,
        #
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