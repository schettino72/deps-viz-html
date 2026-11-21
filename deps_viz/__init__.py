"""
Interactive HTML visualization for import_deps JSON output.

Usage:
    deps-viz app tests                    # analyze and open in browser
    deps-viz app -o deps.html             # write self-contained HTML file
    import_deps app --json | deps-viz     # read import_deps JSON from stdin
"""

import argparse
import base64
import json
import subprocess
import sys
import tempfile
import webbrowser
import zlib
from pathlib import Path


# Longest URL passed to the browser. Windows limits a command line to 32767 chars.
MAX_URL_LENGTH = 30_000


def slim_results(results):
    """Keep only fields used by the viewer (drops local file paths)"""
    return [{'module': res['module'], 'imports': res['imports']} for res in results]


def format_html(results):
    """Format import_deps JSON results as interactive HTML visualization"""
    template_path = Path(__file__).parent / 'template.html'
    template = template_path.read_text()
    # escape "<" so data can never close the <script> tag
    graph_json = json.dumps(slim_results(results)).replace('<', '\\u003c')
    return template.replace('/*GRAPH_DATA*/null', graph_json)


def encode_fragment(results):
    """Encode results as URL fragment "d=<base64url(deflate-raw(json))>"

    The fragment is never sent to the server, so the data stays in the browser.
    """
    raw = json.dumps(slim_results(results), separators=(',', ':')).encode()
    compressor = zlib.compressobj(level=9, wbits=-15)
    packed = compressor.compress(raw) + compressor.flush()
    return 'd=' + base64.urlsafe_b64encode(packed).decode().rstrip('=')


def viewer_url(base_url, results, max_length=None):
    """URL of hosted viewer with results in the fragment, None if too long"""
    url = base_url + '#' + encode_fragment(results)
    if len(url) > (max_length or MAX_URL_LENGTH):
        return None
    return url


def run_import_deps(paths):
    """Run import_deps on paths, return its JSON results.

    On failure import_deps already printed the error, exit with its code.
    """
    cmd = [sys.executable, '-m', 'import_deps', *paths, '--json']
    proc = subprocess.run(cmd, stdout=subprocess.PIPE, text=True)
    if proc.returncode != 0:
        sys.exit(proc.returncode)
    return json.loads(proc.stdout)


def write_temp_html(results):
    """Write self-contained HTML to a temp file (kept for the browser), return its path"""
    with tempfile.NamedTemporaryFile('w', prefix='deps-viz-', suffix='.html', delete=False) as html_file:
        html_file.write(format_html(results))
    return Path(html_file.name)


def main(argv=None):
    parser = argparse.ArgumentParser(
        prog='deps-viz',
        description='Visualize Python import dependencies in the browser.')
    parser.add_argument('path', metavar='PATH', nargs='*',
                        help='Python file(s) or package directory(s) to analyze. '
                             'If omitted, read import_deps JSON from stdin.')
    parser.add_argument('-o', '--output', metavar='FILE',
                        help='Write self-contained HTML to FILE ("-" for stdout) instead of opening a browser')
    parser.add_argument('--viewer', metavar='URL',
                        help='Open hosted viewer at URL, data passed in the URL fragment '
                             '(falls back to a local file if the URL is too long)')
    config = parser.parse_args(argv)

    if config.path:
        results = run_import_deps(config.path)
    else:
        results = json.load(sys.stdin)

    if config.output == '-':
        print(format_html(results))
        return
    if config.output:
        Path(config.output).write_text(format_html(results))
        return

    url = viewer_url(config.viewer, results) if config.viewer else None
    if url is None:
        url = write_temp_html(results).as_uri()
    webbrowser.open(url)
