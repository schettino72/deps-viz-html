# deps-viz

Interactive HTML visualization for Python import dependencies.

Takes JSON output from `import_deps` and generates a self-contained HTML file with an interactive graph.

## Usage

```bash
# Pipe from import_deps
python -m import_deps app tests --json | python deps_viz.py > deps.html

# Or from a saved JSON file
python deps_viz.py < deps.json > deps.html
```

Then open `deps.html` in a browser.

## Features

- **Layout options**: Hierarchical (LR/TB) using dagre, or force-directed
- **Zoom/pan**: Mouse wheel and drag
- **Click node**: Highlights its imports and importers
- **Search**: Filter modules by name
- **Package filters**: Toggle packages on/off (recalculates layout)
- **Cycle detection**: Circular dependencies highlighted in red

## Dependencies

None for the Python script. The generated HTML loads D3.js and dagre from CDN.

## Related

- [import_deps](https://github.com/schettino72/import-deps) - Analyzes Python import dependencies
