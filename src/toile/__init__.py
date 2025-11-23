"""
Toile - Tools for working with astrocyte dynamics data

This package provides utilities for importing microscopy TIFF stacks
and exporting them to WebDataset format for machine learning pipelines.
"""

from typer import Typer

from .export import app as export_app


##

app = Typer()

app.add_typer( export_app, name = 'export' )


##

def main():
    """Entry point for the toile CLI application."""
    app()


##

if __name__ == '__main__':
    main()


##