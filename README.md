# toile

**Tools for working with astrocyte dynamics data**

Toile is a Python package for converting microscopy TIFF stacks into WebDataset format for machine learning pipelines. It handles OME-TIFF metadata extraction, batch processing, and creates sharded tar archives optimized for distributed training.

## Features

- **OME-TIFF Support**: Automatic extraction of spatial, temporal, and experimental metadata from OME-TIFF XML annotations
- **Batch Processing**: Process multiple recordings using glob patterns or YAML configuration files
- **Custom Metadata Parsing**: Flexible filename parsing system for extracting experimental identifiers
- **Sharded Archives**: Configurable shard sizes for WebDataset format (850MB standard, 38MB for Bluesky PDS)
- **ML-Ready**: Optional uint8 normalization for efficient model training
- **atdata Integration**: Built on the atdata PackableSample framework for data transformation pipelines

## Installation

Install using `uv` (recommended) or `pip`:

```bash
# Using uv
uv pip install toile

# Using pip
pip install toile
```

For development:

```bash
git clone https://github.com/forecast-bio/toile.git
cd toile
uv sync --all-extras --dev
```

## Quick Start

Export a TIFF stack to WebDataset format:

```bash
# Basic usage - export frames from a single recording
toile export frames /path/to/recording/ /output/dataset

# With uint8 normalization for ML
toile export frames /path/to/recording/ /output/dataset --uint8 --verbose

# Batch processing with glob patterns
toile export frames "/data/*/recording*/" /output/dataset --stem my_dataset

# Using PDS-compatible shard size for Bluesky
toile export frames /data/recordings/ /output/dataset --pds
```

## CLI Commands

### `toile export frames`

Convert TIFF stacks to WebDataset format as individual frames.

```bash
toile export frames INPUT OUTPUT [OPTIONS]
```

**Arguments:**
- `INPUT`: Path to TIFF directory or YAML config file
- `OUTPUT`: Output directory for tar archives

**Options:**
- `--stem TEXT`: Custom stem for output filenames (default: output directory name)
- `--shard-size INT`: Maximum shard size in bytes (default: auto-selected)
- `--pds`: Use PDS-compatible shard size (38MB for Bluesky)
- `--uint8`: Normalize images to uint8 (0-255) range
- `--compressed`: Enable compression (not yet implemented)
- `--verbose`: Print detailed progress information

**Examples:**

```bash
# Export single recording with verbose output
toile export frames /data/mouse_123/recording_001/ /output/dataset --verbose

# Batch export with custom naming
toile export frames "/data/experiment_*/*.tif" /output/dataset --stem exp2024

# ML-ready export with normalization
toile export frames /data/recordings/ /output/dataset --uint8 --pds
```

### `toile export test-frames`

Generate a synthetic test dataset for development and testing.

```bash
toile export test-frames OUTPUT [OPTIONS]
```

**Arguments:**
- `OUTPUT`: Output directory for test dataset

**Options:**
- `--stem TEXT`: Custom stem for output filenames
- `--compressed`: Enable gzip compression

**Example:**

```bash
toile export test-frames /tmp/test_dataset --compressed
```

## Configuration Files

For complex batch processing, use YAML configuration files:

```yaml
# config.yaml
inputs:
  - "/data/experiment1/**/*.tif"
  - "/data/experiment2/**/*.tif"

output_stem: "astrocyte_dataset"
shard_size: 38000000  # 38MB for PDS compatibility
to_uint8: true

# Optional: Extract metadata from filenames
filename_spec:
  template: "mouse_{mouse_id}_slice_{slice_id}_{date}.tif"
  transforms:
    mouse_id: int
    slice_id: identity
    date: date_compact
```

Then run:

```bash
toile export frames config.yaml /output/dataset
```

## Data Schema

Toile uses structured schemas built on the `atdata` framework:

- **Movie**: Full TIFF stack with metadata
- **Frame**: Individual image frame with combined metadata
- **SliceRecordingFrame**: Experimental frames with mouse/slice identifiers
- **ImageSample**: Minimal image data for ML pipelines

Metadata includes acquisition timestamps, physical scales, stage positions, and channel information extracted from OME-TIFF annotations.

## Output Format

WebDataset tar archives contain samples with the following structure:

```
sample-000000-000.npy    # Image data as numpy array
sample-000000-000.json   # Metadata dictionary
sample-000000-001.npy
sample-000000-001.json
...
```

Each shard is automatically numbered (e.g., `dataset-000000.tar`, `dataset-000001.tar`) when the size limit is reached.

## Development

Run tests:

```bash
uv run pytest
```

Build package:

```bash
uv build
```

## License

This project is licensed under the MIT License - see the [LICENSE](LICENSE) file for details.

## Acknowledgments

Built with:
- [atdata](https://github.com/foundation-ac/atdata) - Streaming schematized datasets framework
- [webdataset](https://github.com/webdataset/webdataset) - Efficient streaming datasets for ML and more
- [scikit-image](https://scikit-image.org/) - Some good standard impl for image basics
