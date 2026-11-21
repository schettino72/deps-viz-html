"""
Interactive HTML visualization for import_deps JSON output.

Usage:
    python -m import_deps app tests --json | python -m deps_viz > deps.html
    python -m deps_viz < deps.json > deps.html
"""

import base64
import json
import sys
import zlib
from pathlib import Path


def format_html(results):
    """Format import_deps JSON results as interactive HTML visualization"""
    template_path = Path(__file__).parent / 'template.html'
    template = template_path.read_text()
    # escape "<" so data can never close the <script> tag
    graph_json = json.dumps(results).replace('<', '\\u003c')
    return template.replace('/*GRAPH_DATA*/null', graph_json)


def encode_fragment(results):
    """Encode results as URL fragment "d=<base64url(deflate-raw(json))>"

    The fragment is never sent to the server, so the data stays in the browser.
    """
    raw = json.dumps(results, separators=(',', ':')).encode()
    compressor = zlib.compressobj(level=9, wbits=-15)
    packed = compressor.compress(raw) + compressor.flush()
    return 'd=' + base64.urlsafe_b64encode(packed).decode().rstrip('=')


def main():
    results = json.load(sys.stdin)
    print(format_html(results))
