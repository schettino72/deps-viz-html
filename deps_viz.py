#!/usr/bin/env python3
"""
Standalone visualization script for import_deps JSON output.

Usage:
    python -m import_deps app tests --json | python deps_viz.py > deps.html
    python deps_viz.py < deps.json > deps.html
"""

import json
import sys
from pathlib import Path


def detect_cycles(results):
    """Detect circular dependencies using DFS
    Returns set of edges (module, import) that create cycles
    """
    graph = {}
    for result in results:
        module = result['module']
        graph[module] = result['imports']

    cycle_edges = set()
    visited = set()
    rec_stack = set()

    def dfs(node, path):
        visited.add(node)
        rec_stack.add(node)
        path.append(node)

        for neighbor in graph.get(node, []):
            if neighbor not in visited:
                if neighbor in graph:
                    dfs(neighbor, path)
            elif neighbor in rec_stack:
                cycle_start_idx = path.index(neighbor)
                for i in range(cycle_start_idx, len(path)):
                    if i + 1 < len(path):
                        cycle_edges.add((path[i], path[i + 1]))
                cycle_edges.add((node, neighbor))

        rec_stack.remove(node)
        path.pop()

    for module in graph:
        if module not in visited:
            dfs(module, [])

    return cycle_edges


def format_html(results, cycle_edges):
    """Format results as interactive HTML visualization"""
    cycle_edges_list = [[src, dst] for src, dst in cycle_edges]

    nodes = []
    links = []

    for result in results:
        module = result['module']
        pkg = module.rsplit('.', 1)[0] if '.' in module else ''
        nodes.append({'id': module, 'package': pkg})

        for imp in result['imports']:
            links.append({'source': module, 'target': imp})

    graph_data = json.dumps({'nodes': nodes, 'links': links, 'cycles': cycle_edges_list})

    # Read template
    template_path = Path(__file__).parent / 'template.html'
    template = template_path.read_text()

    # Inject data
    html = template.replace('/*GRAPH_DATA*/null', graph_data)

    return html


def main():
    data = json.load(sys.stdin)
    cycle_edges = detect_cycles(data)
    print(format_html(data, cycle_edges))


if __name__ == '__main__':
    main()
