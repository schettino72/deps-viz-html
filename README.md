# deps-viz

Interactive HTML visualization for Python import dependencies.

Analyzes your code with `import_deps` and opens an interactive graph in the browser.

## Usage

```bash
# Analyze and open in browser (writes a temp file in /tmp)
deps-viz app tests

# Write a self-contained HTML file, then open it in your browser
deps-viz app tests -o deps.html
xdg-open deps.html        # Linux; macOS: open deps.html

# Read import_deps JSON from stdin
import_deps app --json | deps-viz -o deps.html
```

You can also drag `deps.html` into a browser window.

**Snap browsers (default Firefox and Chromium on Ubuntu):** opening directly
(without `-o`) fails with "file not found", because snaps have a private `/tmp`.
Use `-o` and keep the HTML file somewhere under your home directory.

## Examples

Open directly in a browser, no install needed:

- [examples/sample.html](examples/sample.html) - small sample (7 modules)
- [examples/rich.html](examples/rich.html) - the [rich](https://github.com/Textualize/rich) library (100 modules)

## Features

- **Layout options**: Hierarchical (LR/TB) using dagre, or force-directed
- **Zoom/pan**: Mouse wheel and drag
- **Click node**: Highlights its imports and importers
- **Search**: Filter modules by name
- **Package filters**: Toggle packages on/off (recalculates layout)
- **Cycle detection**: Circular dependencies highlighted in red

## Dependencies

[import_deps](https://github.com/schettino72/import-deps). The HTML loads Cytoscape.js and cytoscape-dagre from CDN.

## Related

- [import_deps](https://github.com/schettino72/import-deps) - Analyzes Python import dependencies
