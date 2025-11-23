# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Project Overview

`toile` is a Python package for working with astrocyte dynamics data. It processes TIFF image stacks (particularly OME-TIFF format) from microscopy recordings and exports them to WebDataset format for machine learning workflows.

## Development Commands

### Package Management
This project uses `uv` for dependency management:
```bash
# Install dependencies (including dev dependencies)
uv sync --all-extras --dev

# Install package in editable mode
uv pip install -e .
```

### Running Tests
```bash
# Run all tests
uv run pytest

# Run tests with coverage
uv run pytest --cov
```

### Building and Publishing
```bash
# Build distribution
uv build

# Publish to PyPI (requires UV_PUBLISH_TOKEN)
uv publish
```

### Running the CLI
```bash
# As a module
python -m toile

# Using the installed command
toile

# Export TIFF frames to WebDataset format
toile export frames <input> <output> [--stem <name>] [--uint8] [--verbose]
```

## Architecture

### Core Data Flow

1. **TIFF Import** (`tiff_import.py`): Loads TIFF stacks from microscopy recordings
   - Supports OME-TIFF metadata extraction using `tifffile` and `xmltodict`
   - Parses frame-level metadata (position, timing, UUIDs)
   - Handles multi-channel recordings
   - Optional uint8 normalization for ML pipelines

2. **Schema Definitions** (`schema.py`): Data structures built on `atdata` (a PackableSample framework)
   - `Movie`: Container for full TIFF stacks with metadata
   - `Frame`: Individual image frames with metadata
   - `SliceRecordingFrame`: Experimental session frames with mouse/slice identifiers
   - `ImageSample`: Simplified image data for ML
   - Uses `atdata.lens` for data transformations between representations

3. **Export Pipeline** (`export.py`): Converts TIFF data to WebDataset format
   - Processes individual TIFF files or batch configs (YAML)
   - Writes to sharded tar archives using `webdataset` library
   - Configurable shard sizes (default 850MB, or 38MB for PDS/Bluesky compatibility)
   - Supports glob patterns for batch processing

### CLI Structure

The CLI uses Typer for command routing:
- Main app in `__init__.py` with subcommands
- `export` subcommand group in `export.py`
  - `export frames`: Convert TIFFs to per-frame WebDataset archives
  - `export test-frames`: Generate synthetic test datasets

### Key Dependencies

- `atdata`: Data structure framework for packable samples
- `webdataset`: Efficient dataset format for ML pipelines
- `scikit-image` & `tifffile`: TIFF file handling
- `typer`: CLI framework
- `xmltodict`: OME metadata parsing

### Filename Parsing

The `tiff_import.py` module includes a flexible filename parsing system:
- `_make_filename_parser()`: Creates custom parsers from template + transforms
- Built-in transforms: `identity`, `float`, `int`, `split_age_sex`, `date_compact`
- Used to extract experimental metadata from file naming conventions

### Metadata Collation

OME-TIFF metadata is extracted and normalized:
- `_collate_frame_metadata()`: Per-frame position, timing, UUID data
- `_collate_metadata()`: Image-level acquisition date, physical scales, channel info
- Metadata flows through `Movie` → `Frame` → WebDataset samples

## Testing

Tests are located in the `tests/` directory (currently empty). When adding tests:
- Use pytest as the test framework
- Test coverage is enabled with pytest-cov
- CI runs tests on push to main and release branches via GitHub Actions
