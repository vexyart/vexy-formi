# VexyFormi

Fast code formatting and minification using the best available tools.

## Features

- 🔥 **Blazing Fast**: Uses fastest available tools (esbuild, swc, biome, ruff)
- 🛡️ **Safe**: Atomic operations with automatic backups
- 🎯 **Smart**: Automatic tool detection and fallbacks
- 📦 **Simple**: Zero-config operation with sensible defaults
- 🌐 **Universal**: Supports JS, TS, CSS, HTML, Python, JSON, YAML, TOML, Markdown

## Quick Start

```bash
# Install
pip install vexy-formi

# Install all required tools automatically
vfor install

# Minify current directory
vfor mini

# Format Python files
vfor fmt --verbose src/

# Show available tools
vfor tools

# Update all tools to latest versions
vfor update

# Use as Python package
python -c "import vexy_formi; vexy_formi.minify('src/')"
```

## Supported Tools

- **JavaScript/TypeScript**: esbuild, swc, terser, biome, prettier
- **CSS/SCSS**: biome, lightningcss, prettier
- **Python**: ruff, black  
- **HTML**: html-minifier-terser, prettier
- **JSON**: biome, jq, prettier
- **TOML**: taplo, dprint
- **YAML**: prettier, yq
- **Markdown**: dprint, prettier

## Configuration

Set preferences via environment variables:
- `VFOR_PREFERRED_JS_TOOL=esbuild`
- `VFOR_PREFERRED_CSS_TOOL=biome`
- `VFOR_PREFERRED_PYTHON_TOOL=ruff`
- `VFOR_MAX_WORKERS=8`

Or create `.vfor.json` in your project:
```json
{
    "preferred_js_tool": "esbuild",
    "preferred_css_tool": "biome", 
    "max_workers": 4
}
```

## CLI Usage

```bash
# Minify files
vfor mini                    # Current directory  
vfor mini src/              # Specific directory
vfor mini --verbose src/    # Show detailed output
vfor mini --no-backup src/  # Skip backups

# Format files
vfor fmt                     # Current directory
vfor fmt --recursive src/    # Process recursively  
vfor fmt --exclude "*.min.*" # Exclude patterns

# Tool management
vfor install                 # Install all required tools
vfor update                  # Update tools to latest versions
vfor tools                   # Show available tools
vfor cleanup                 # Clean backup files
```

## Python API

```python
import vexy_formi

# Simple API
result = vexy_formi.minify('src/')
result = vexy_formi.format('src/', recursive=True, exclude=['*.test.*'])

# Advanced usage
from vexy_formi import FileProcessor

processor = FileProcessor()
result = processor.minify_files(
    Path('src/'), 
    recursive=True,
    max_workers=8,
    create_backup=True
)

print(f"Processed {result.total_files} files")
print(f"Size reduction: {result.total_size_reduction_percent:.1f}%")
```

## Development

```bash
# Clone repository
git clone https://github.com/vexyart/vexy-formi.git
cd vexy-formi

# Install dependencies  
pip install -e .[dev,test]

# Run CLI directly
./vfor mini examples/

# Run tests
pytest

# Format code
ruff format src/
```

## License

MIT License