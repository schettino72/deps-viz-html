# deps-viz

Interactive HTML visualization for Python import dependencies.

Analyzes your code with `import_deps` and opens an interactive graph in the browser.

## Install

```bash
pip install deps-viz

# or as a standalone command with uv
uv tool install deps-viz

# or run without installing
uvx deps-viz app tests
```

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

## Input format

deps-viz reads the JSON produced by `import_deps --json`: a list with one entry per module.

```json
[
  {"module": "foo.__init__", "imports": []},
  {"module": "foo.foo_a", "imports": ["foo.foo_b", "foo.sub.sub_a"]},
  {"module": "foo.foo_b", "imports": []},
  {"module": "foo.sub.sub_a", "imports": ["foo.foo_b"]}
]
```

- `module`: dotted module name. Its package is everything before the last dot
  (`foo.sub.sub_a` -> `foo.sub`), used for package colors, filters and collapsing.
- `imports`: names of modules it imports.
  Imports of modules not in the list (stdlib, third-party) are ignored.
- Other fields (e.g. `filepath`, `all_imports`) are ignored.

The format is not Python specific: any tool producing this JSON can use deps-viz
(`deps-viz -o deps.html < graph.json`). `import_deps` is only used by `deps-viz PATH`.

## Examples

Open in your browser, no install needed:

- [sample](https://raw.githack.com/schettino72/deps-viz-html/main/examples/sample.html) - small sample (7 modules)
- [rich](https://raw.githack.com/schettino72/deps-viz-html/main/examples/rich.html) - the [rich](https://github.com/Textualize/rich) library (100 modules)

Source files are in [examples/](https://github.com/schettino72/deps-viz-html/tree/main/examples).

## Features

- **Layout options**: Hierarchical (LR/TB) using dagre, or force-directed
- **Zoom/pan**: Mouse wheel and drag
- **Click node**: Highlights its imports and importers
- **Search**: Filter modules by name
- **Package filters**: Toggle packages on/off (recalculates layout)
- **Cycle detection**: Circular dependencies highlighted in red

## Dependencies

[import_deps](https://github.com/schettino72/import-deps) (no dependencies of its own), used to analyze code with `deps-viz PATH`.
The HTML loads Cytoscape.js and cytoscape-dagre from CDN.

## Related

- [import_deps](https://github.com/schettino72/import-deps) - Analyzes Python import dependencies
