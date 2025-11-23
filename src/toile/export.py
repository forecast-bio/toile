"""
Export utilities for converting TIFF stacks to WebDataset format.

This module provides the core export pipeline for converting microscopy
TIFF recordings into WebDataset tar archives for machine learning workflows.
Supports batch processing via config files, glob patterns, and configurable
shard sizes for compatibility with different storage backends (e.g., Bluesky PDS).
"""

##
# Imports

from typer import Typer

#

import warnings

import os
from glob import glob
from pathlib import (
    Path,
)
import gzip

import json, yaml
from dataclasses import dataclass

from tqdm import tqdm
import numpy as np
import webdataset as wds

#

import toile.schema as schema
from ._common import (
    _Pathable,
)
from .tiff_import import (
    load_tiff,
    _FilenameParser,
    _make_filename_parser,
)

#

from typing import (
    TypeAlias,
    Literal,
    Optional,
    Sequence,
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
    """Write individual frames from a Movie to a WebDataset writer.

    Splits a Movie into individual Frame samples and writes them to the
    WebDataset archive with sequential keys.

    Args:
        ds: Movie object containing frames and metadata
        dest: WebDataset ShardWriter or TarWriter to write samples to
        key_template: Optional format string for sample keys (default: 'sample{i:06d}')
            Can use {i_dataset} for global index, {i_group} for frame index
        i_start: Starting index for sample numbering

    Returns:
        Final sample index after writing all frames
    """
    ##

    # Normalize args
    if key_template is None:
        key_template = 'sample{i:06d}'

    #

    movie_metadata = (
        dict() if ds.metadata is None
        else { k: v
               for k, v in ds.metadata.items() }
    )
    frame_metadata = (
        ds.frame_metadata if ds.frame_metadata is not None
        else [ None for _ in range( ds.frames.shape[0] ) ]
    )
    
    i_dataset = i_start
    for i_movie, cur_frame_meta in (
        zip(
            range( ds.frames.shape[0] ),
            frame_metadata,
        )
    ):
        cur_metadata = { k: v for k, v in movie_metadata.items() }
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


## Config parsing

@dataclass
class ExportConfig:
    """Configuration for TIFF export operations.

    Can be loaded from YAML files for batch processing or constructed
    programmatically. Specifies input file patterns, output settings,
    and optional filename parsing.

    Attributes:
        inputs: List of file paths or glob patterns for input TIFF files
        output_stem: Optional stem for output tar archive names (default: output directory name)
        shard_size: Maximum size in bytes for each tar shard (default: 850MB)
        to_uint8: Whether to normalize images to uint8 (0-255) range
        compressed: Whether to compress output tar files (not yet implemented)
        filename_parser: Optional parser function for extracting metadata from filenames
    """
    ##

    # Required
    inputs: list[str]
    """List of file paths or glob patterns for input TIFF files"""

    # Optional
    output_stem: str | None = None
    """Optional stem for output tar archive names (default: output directory name)"""
    shard_size: int = 850_000_000
    """Maximum size in bytes for each tar shard (default: 850MB for WebDataset standard)"""
    to_uint8: bool = False
    """Whether to normalize images to uint8 (0-255) range"""
    compressed: bool = False
    """Whether to compress output tar files (not yet implemented)"""

    filename_parser: _FilenameParser | None = None
    """Optional parser function for extracting metadata from filenames"""

def _parse_config( input_path: _Pathable ) -> ExportConfig:
    """Load an ExportConfig from a YAML configuration file.

    The YAML file should contain keys matching ExportConfig attributes.
    Optionally includes a 'filename_spec' section with 'template' and
    'transforms' for custom filename parsing.

    Args:
        input_path: Path to YAML configuration file

    Returns:
        ExportConfig object with settings from the YAML file

    Example YAML format:
        inputs:
          - "/path/to/data/**/*.tif"
        output_stem: "my_dataset"
        shard_size: 38000000
        to_uint8: true
        filename_spec:
          template: "mouse_{mouse_id}_slice_{slice_id}.tif"
          transforms:
            mouse_id: int
            slice_id: identity
    """

    with open( input_path, 'r' ) as f:
        ret_data = yaml.safe_load( f )

    if 'filename_spec' in ret_data:
        # Cache
        filename_spec = ret_data['filename_spec']
        del ret_data['filename_spec']
    else:
        filename_spec = None
    
    ret = ExportConfig( **ret_data )

    if filename_spec is not None:
        ret.filename_parser = _make_filename_parser(
            filename_spec['template'],
            filename_spec['transforms'],
        )

    return ret


##
# Common

ExportKind: TypeAlias = Literal[
    'movies',
    'frames',
]

def export_tiffs(
        _inputs: Sequence[_Pathable],
        _output_dir: _Pathable,
        _stem: str | None = None,
        #
        kind: ExportKind = 'movies',
        to_uint8: bool = False,
        filename_parser: _FilenameParser | None = None,
        #
        shard_size: float = 38_000_000.,
        compressed: bool = False,
        #
        verbose: bool = False,
        #
        **kwargs
    ) -> None:
    """Export TIFF files to WebDataset format with configurable options.

    Main export pipeline that loads TIFF stacks, extracts metadata, and
    writes samples to sharded tar archives. Supports glob patterns for
    batch processing and reports success/failure statistics.

    Args:
        _inputs: List of file paths or glob patterns for input TIFF directories
        _output_dir: Output directory for tar archives
        _stem: Optional stem for output filenames (default: output directory name)
        kind: Export type - 'movies' (full stacks), 'frames' (individual frames), or 'clips'
        to_uint8: Normalize images to uint8 (0-255) range
        filename_parser: Optional function to extract metadata from filenames
        shard_size: Maximum size in bytes for each tar shard
        compressed: Enable compression (not yet implemented)
        verbose: Print detailed progress messages
        **kwargs: Additional arguments passed to WebDataset writer

    Returns:
        None (writes files to disk)

    Example:
        >>> export_tiffs(
        ...     ["/data/experiment1/*.tif", "/data/experiment2/*.tif"],
        ...     "/output/dataset",
        ...     stem="astrocyte_recordings",
        ...     kind="frames",
        ...     to_uint8=True,
        ...     verbose=True
        ... )
    """
    ##

    def _printv( *a, **b ):
        if verbose:
            print( *a, **b )

    # Normalize args
    inputs: list[Path] = [ Path( p )
                           for p in _inputs ]
    output_dir = Path( _output_dir )
    stem = (
        Path( output_dir ).stem if _stem is None
        else _stem
    )

    if kind == 'frames':
        key_template = 'tseries-{i_dataset}-frame-{i_group}'
    else:
        # TODO Make explicit for other types
        key_template = 'sample-{i_dataset}-{i_group}'

    # Setup output directory
    output_dir.mkdir( parents = True, exist_ok = True )
    output_pattern = (output_dir / f'{stem}-%06d.tar').as_posix()

    # Parse input globs
    input_globs = [ glob( p.as_posix() )
                    for p in inputs ]
    
    input_paths = []
    for g in input_globs:
        input_paths += [ Path( p )
                         for p in g ]

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
                cur_ds = load_tiff( cur_input_path,
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
        kind: ExportKind = 'frames',
        #
        compressed: bool = False,
        #
        **kwargs
    ) -> None:
    """Generate a synthetic test dataset in WebDataset format.

    Creates random image data for testing WebDataset pipelines without
    requiring actual microscopy data. Useful for development and testing.

    Args:
        output_dir: Directory to write test dataset
        stem: Optional stem for output filenames (default: output directory name)
        kind: Dataset type - currently only 'frames' is supported
        compressed: Enable gzip compression of tar files
        **kwargs: Additional arguments passed to WebDataset ShardWriter

    Returns:
        None (writes files to disk)

    Example:
        >>> export_test("/tmp/test_dataset", kind="frames", compressed=True)
    """

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

    if kind == 'frames':

        print( 'Exporting frames ...' )

        with wds.writer.ShardWriter( wds_pattern, **kwargs ) as sink:
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

@app.command( 'test-frames' )
def _cli_export_test_frames(
            output: str,
            stem: str = '',
            compressed: bool = False,
        ):
    """CLI command: Generate a synthetic test dataset of random frames.

    Usage: toile export test-frames OUTPUT [--stem STEM] [--compressed]
    """
    export_test( output, stem,
        compressed = compressed,
        #
        kind = 'frames',
    )

def _standardize_config_args(
                input: _Pathable,
                stem: str = '',
                #
                shard_size: int = -1,
                pds: bool = False,
                #
                uint8: bool = False,
                compressed: bool = False,
            ) -> ExportConfig:
    """Normalize CLI arguments into an ExportConfig object.

    Handles both YAML config files and direct file path inputs. Sets
    appropriate default shard sizes based on target platform.

    Args:
        input: Path to YAML config file or direct input file/glob pattern
        stem: Optional output filename stem
        shard_size: Maximum shard size in bytes (-1 for auto-selection)
        pds: If True, use PDS-compatible shard size (38MB for Bluesky)
        uint8: Normalize images to uint8 range
        compressed: Enable compression

    Returns:
        ExportConfig object with normalized settings
    """

    if shard_size < 0:
        # Set default shard sizes based on target

        if pds:
            # Limit for Bsky default PDS blob limit
            shard_size = 38_000_000
        else:
            # Keep to `wds` standard of ≤ 1GB per shard (with overhead)
            shard_size = 850_000_000

    input_path = Path( input )
    if input_path.suffix in ('.yaml', '.yml'):
        ret = _parse_config( input_path )

    else:
        ret = ExportConfig(
            inputs = [ input_path.as_posix() ],
            output_stem = None if len( stem ) == 0 else stem,
            shard_size = shard_size,
            to_uint8 = uint8,
            compressed = compressed,
        )
    
    return ret

# @app.command( 'movies' )
# def _cli_export_movies(
#             input: str,
#             output: str,
#             stem: str = '',
#         ):
#     export_tiffs( input, output, stem, kind = 'movies' )

@app.command( 'frames' )
def _cli_export_frames(
            input: Path,
            output: Path,
            stem: str = '',
            #
            shard_size: int = -1,
            pds: bool = False,
            #
            uint8: bool = False,
            compressed: bool = False,
            #
            verbose: bool = False,
        ):
    """CLI command: Export TIFF stacks to WebDataset format as individual frames.

    Processes TIFF directories or uses a YAML config file for batch processing.
    Extracts OME-TIFF metadata and writes sharded tar archives.

    Usage: toile export frames INPUT OUTPUT [OPTIONS]

    Args:
        input: Path to TIFF directory or YAML config file
        output: Output directory for tar archives
        stem: Optional output filename stem
        shard_size: Maximum shard size in bytes (-1 for auto)
        pds: Use PDS-compatible shard size (38MB for Bluesky)
        uint8: Normalize images to uint8 (0-255) range
        compressed: Enable compression (not yet implemented)
        verbose: Print detailed progress information

    Example:
        toile export frames /data/recordings /output/dataset --uint8 --verbose
        toile export frames config.yaml /output/dataset --pds
    """

    config = _standardize_config_args(
        input, stem, shard_size, pds, uint8, compressed,
    )

    # TODO Implement compresison
    if config.compressed:
        warnings.warn( '* Compression not yet implemented' )

    export_tiffs(
        config.inputs,
        output,
        config.output_stem,
        #
        to_uint8 = config.to_uint8,
        shard_size = float( config.shard_size ),
        filename_parser = config.filename_parser,
        #
        verbose = verbose,
        #
        kind = 'frames'
    )


##