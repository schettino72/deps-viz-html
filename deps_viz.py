#!/usr/bin/env python3
"""
Standalone visualization script for import_deps JSON output.

Usage:
    python -m import_deps app tests --json | python deps_viz.py > deps.html
    python deps_viz.py < deps.json > deps.html
"""

import json
import sys


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
    """Format results as interactive HTML visualization using D3.js"""
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

    html = '''<!DOCTYPE html>
<html>
<head>
    <meta charset="utf-8">
    <title>Import Dependencies</title>
    <script src="https://d3js.org/d3.v7.min.js"></script>
    <style>
        * { margin: 0; padding: 0; box-sizing: border-box; }
        body { font-family: -apple-system, BlinkMacSystemFont, "Segoe UI", Roboto, sans-serif; }
        #container { display: flex; height: 100vh; }
        #sidebar {
            width: 280px;
            padding: 15px;
            background: #f5f5f5;
            border-right: 1px solid #ddd;
            overflow-y: auto;
        }
        #graph { flex: 1; }
        svg { width: 100%; height: 100%; }
        .node { cursor: pointer; }
        .node circle { stroke: #fff; stroke-width: 2px; }
        .node text { font-size: 11px; pointer-events: none; }
        .link { fill: none; stroke-opacity: 0.6; }
        .link.cycle { stroke: #e74c3c !important; stroke-width: 2.5px; }
        .dimmed { opacity: 0.15; }
        h3 { margin-bottom: 10px; color: #333; font-size: 14px; }
        #search {
            width: 100%;
            padding: 8px;
            margin-bottom: 15px;
            border: 1px solid #ccc;
            border-radius: 4px;
            font-size: 13px;
        }
        .filter-section { margin-bottom: 20px; }
        .package-filter {
            display: flex;
            align-items: center;
            padding: 4px 0;
            font-size: 13px;
        }
        .package-filter input { margin-right: 8px; }
        .color-dot {
            width: 12px;
            height: 12px;
            border-radius: 50%;
            display: inline-block;
            margin-right: 6px;
        }
        #info {
            background: white;
            padding: 12px;
            border-radius: 6px;
            border: 1px solid #ddd;
            font-size: 12px;
        }
        #info h4 { margin-bottom: 8px; color: #2c3e50; }
        #info ul { margin-left: 18px; margin-top: 5px; }
        #info li { margin: 3px 0; }
        .info-section { margin-top: 10px; }
        .legend { margin-top: 20px; font-size: 12px; }
        .legend-item { display: flex; align-items: center; margin: 5px 0; }
        #reset-btn {
            width: 100%;
            padding: 8px;
            margin-top: 10px;
            background: #3498db;
            color: white;
            border: none;
            border-radius: 4px;
            cursor: pointer;
            font-size: 13px;
        }
        #reset-btn:hover { background: #2980b9; }
    </style>
</head>
<body>
    <div id="container">
        <div id="sidebar">
            <h3>Search</h3>
            <input type="text" id="search" placeholder="Filter modules...">
            <div class="filter-section">
                <h3>Packages</h3>
                <div id="package-filters"></div>
            </div>
            <button id="reset-btn">Reset View</button>
            <div id="info">
                <h4>Module Info</h4>
                <p>Click a node to see details</p>
            </div>
            <div class="legend">
                <h3>Legend</h3>
                <div class="legend-item">
                    <svg width="30" height="12"><line x1="0" y1="6" x2="30" y2="6" stroke="#999" stroke-width="1.5"></line></svg>
                    <span style="margin-left:8px">Import</span>
                </div>
                <div class="legend-item">
                    <svg width="30" height="12"><line x1="0" y1="6" x2="30" y2="6" stroke="#e74c3c" stroke-width="2.5"></line></svg>
                    <span style="margin-left:8px">Circular dependency</span>
                </div>
            </div>
        </div>
        <div id="graph"></div>
    </div>
    <script>
    const data = ''' + graph_data + ''';

    // Color scale for packages
    const packages = [...new Set(data.nodes.map(n => n.package))].sort();
    const color = d3.scaleOrdinal(d3.schemeTableau10).domain(packages);

    // Create cycle edge lookup
    const cycleSet = new Set(data.cycles.map(c => c[0] + '|' + c[1]));

    // Setup SVG
    const container = document.getElementById('graph');
    const width = container.clientWidth;
    const height = container.clientHeight;

    const svg = d3.select('#graph')
        .append('svg')
        .attr('viewBox', [0, 0, width, height]);

    // Add zoom
    const g = svg.append('g');
    svg.call(d3.zoom()
        .scaleExtent([0.1, 4])
        .on('zoom', (event) => g.attr('transform', event.transform)));

    // Arrow marker
    svg.append('defs').append('marker')
        .attr('id', 'arrow')
        .attr('viewBox', '0 -5 10 10')
        .attr('refX', 20)
        .attr('refY', 0)
        .attr('markerWidth', 6)
        .attr('markerHeight', 6)
        .attr('orient', 'auto')
        .append('path')
        .attr('fill', '#999')
        .attr('d', 'M0,-5L10,0L0,5');

    svg.append('defs').append('marker')
        .attr('id', 'arrow-cycle')
        .attr('viewBox', '0 -5 10 10')
        .attr('refX', 20)
        .attr('refY', 0)
        .attr('markerWidth', 6)
        .attr('markerHeight', 6)
        .attr('orient', 'auto')
        .append('path')
        .attr('fill', '#e74c3c')
        .attr('d', 'M0,-5L10,0L0,5');

    // Create simulation
    const simulation = d3.forceSimulation(data.nodes)
        .force('link', d3.forceLink(data.links).id(d => d.id).distance(120))
        .force('charge', d3.forceManyBody().strength(-400))
        .force('center', d3.forceCenter(width / 2, height / 2))
        .force('collision', d3.forceCollide().radius(40));

    // Draw links
    const link = g.append('g')
        .selectAll('line')
        .data(data.links)
        .join('line')
        .attr('class', d => {
            const key = d.source.id + '|' + d.target.id;
            return cycleSet.has(key) ? 'link cycle' : 'link';
        })
        .attr('stroke', d => {
            const key = (d.source.id || d.source) + '|' + (d.target.id || d.target);
            return cycleSet.has(key) ? '#e74c3c' : '#999';
        })
        .attr('stroke-width', d => {
            const key = (d.source.id || d.source) + '|' + (d.target.id || d.target);
            return cycleSet.has(key) ? 2.5 : 1.5;
        })
        .attr('marker-end', d => {
            const key = (d.source.id || d.source) + '|' + (d.target.id || d.target);
            return cycleSet.has(key) ? 'url(#arrow-cycle)' : 'url(#arrow)';
        });

    // Draw nodes
    const node = g.append('g')
        .selectAll('.node')
        .data(data.nodes)
        .join('g')
        .attr('class', 'node')
        .call(d3.drag()
            .on('start', dragstarted)
            .on('drag', dragged)
            .on('end', dragended));

    node.append('circle')
        .attr('r', 8)
        .attr('fill', d => color(d.package));

    node.append('text')
        .attr('dx', 12)
        .attr('dy', 4)
        .text(d => d.id.split('.').pop());

    // Tick function
    simulation.on('tick', () => {
        link
            .attr('x1', d => d.source.x)
            .attr('y1', d => d.source.y)
            .attr('x2', d => d.target.x)
            .attr('y2', d => d.target.y);
        node.attr('transform', d => `translate(${d.x},${d.y})`);
    });

    // Drag functions
    function dragstarted(event) {
        if (!event.active) simulation.alphaTarget(0.3).restart();
        event.subject.fx = event.subject.x;
        event.subject.fy = event.subject.y;
    }
    function dragged(event) {
        event.subject.fx = event.x;
        event.subject.fy = event.y;
    }
    function dragended(event) {
        if (!event.active) simulation.alphaTarget(0);
        event.subject.fx = null;
        event.subject.fy = null;
    }

    // Node click - highlight connections
    let selectedNode = null;
    node.on('click', (event, d) => {
        event.stopPropagation();
        selectedNode = d;

        const imports = data.links.filter(l => l.source.id === d.id).map(l => l.target.id);
        const importedBy = data.links.filter(l => l.target.id === d.id).map(l => l.source.id);
        const connected = new Set([d.id, ...imports, ...importedBy]);

        node.classed('dimmed', n => !connected.has(n.id));
        link.classed('dimmed', l => l.source.id !== d.id && l.target.id !== d.id);

        // Update info panel
        document.getElementById('info').innerHTML = `
            <h4>${d.id}</h4>
            <div class="info-section">
                <strong>Package:</strong> ${d.package || '(root)'}
            </div>
            <div class="info-section">
                <strong>Imports (${imports.length}):</strong>
                <ul>${imports.map(i => '<li>' + i + '</li>').join('') || '<li>None</li>'}</ul>
            </div>
            <div class="info-section">
                <strong>Imported by (${importedBy.length}):</strong>
                <ul>${importedBy.map(i => '<li>' + i + '</li>').join('') || '<li>None</li>'}</ul>
            </div>
        `;
    });

    // Click background to reset
    svg.on('click', resetHighlight);
    document.getElementById('reset-btn').onclick = () => {
        resetHighlight();
        document.getElementById('search').value = '';
        document.querySelectorAll('#package-filters input').forEach(cb => cb.checked = true);
        updateVisibility();
    };

    function resetHighlight() {
        selectedNode = null;
        node.classed('dimmed', false);
        link.classed('dimmed', false);
        document.getElementById('info').innerHTML = '<h4>Module Info</h4><p>Click a node to see details</p>';
    }

    // Package filters
    const filtersDiv = document.getElementById('package-filters');
    packages.forEach(pkg => {
        const label = document.createElement('label');
        label.className = 'package-filter';
        label.innerHTML = `
            <input type="checkbox" checked data-package="${pkg}">
            <span class="color-dot" style="background:${color(pkg)}"></span>
            ${pkg || '(root)'}
        `;
        filtersDiv.appendChild(label);
    });

    filtersDiv.addEventListener('change', updateVisibility);

    // Search
    document.getElementById('search').addEventListener('input', updateVisibility);

    function updateVisibility() {
        const searchTerm = document.getElementById('search').value.toLowerCase();
        const checkedPackages = new Set(
            [...document.querySelectorAll('#package-filters input:checked')].map(cb => cb.dataset.package)
        );

        node.style('display', d => {
            const matchesSearch = d.id.toLowerCase().includes(searchTerm);
            const matchesPackage = checkedPackages.has(d.package);
            return matchesSearch && matchesPackage ? null : 'none';
        });

        const visibleNodes = new Set(data.nodes.filter(d => {
            const matchesSearch = d.id.toLowerCase().includes(searchTerm);
            const matchesPackage = checkedPackages.has(d.package);
            return matchesSearch && matchesPackage;
        }).map(d => d.id));

        link.style('display', d =>
            visibleNodes.has(d.source.id) && visibleNodes.has(d.target.id) ? null : 'none'
        );
    }
    </script>
</body>
</html>'''
    return html


def main():
    data = json.load(sys.stdin)
    cycle_edges = detect_cycles(data)
    print(format_html(data, cycle_edges))


if __name__ == '__main__':
    main()
