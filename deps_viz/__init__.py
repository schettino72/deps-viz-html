"""
Interactive HTML visualization for import_deps JSON output.

Usage:
    python -m import_deps app tests --json | python -m deps_viz > deps.html
    python -m deps_viz < deps.json > deps.html
"""

import json
import sys
from pathlib import Path


def format_html(results):
    """Format import_deps JSON results as interactive HTML visualization"""
    template_path = Path(__file__).parent / 'template.html'
    template = template_path.read_text()
    # escape "<" so data can never close the <script> tag
    graph_json = json.dumps(results).replace('<', '\\u003c')
    return template.replace('/*GRAPH_DATA*/null', graph_json)


def main():
    results = json.load(sys.stdin)
    print(format_html(results))
