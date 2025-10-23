"""
Utilities for exporting data
"""

##
# Imports

from typer import Typer

from pathlib import (
    Path,
)

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

def cli_export_tiff(
        input_path: Pathable,
        output_dir: Pathable,
        stem: str = '',
        kind: ExportKind = 'movies',
    ) -> None:
    """TODO"""
    print( 'Will do a thing here!' )


##
# Typer app

app = Typer()

@app.command( 'movies' )
def _cli_export_movies(
            input: str,
            output: str,
            stem: str = '',
        ):
    cli_export_tiff( input, output, stem, kind = 'movies' )

@app.command( 'images' )
def _cli_export_images(
            input: str,
            output: str,
            stem: str = '',    
        ):
    cli_export_tiff( input, output, stem, kind = 'images' )


##