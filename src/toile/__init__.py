"""
TODO
"""

from typer import Typer

from .export import app as export_app


##

app = Typer()

app.add_typer( export_app, name = 'export' )


##

def main():
    app()


##

if __name__ == '__main__':
    main()


##