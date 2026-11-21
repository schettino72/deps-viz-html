import contextlib
import io
import json
import pathlib
import tempfile
import unittest
from unittest import mock
from urllib.parse import urlparse
from urllib.request import url2pathname

import deps_viz
from deps_viz import encode_fragment, format_html, main, run_import_deps, viewer_url


SAMPLE_PKG = pathlib.Path(__file__).parent / 'sample-pkg' / 'foo'
SAMPLE_JSON = pathlib.Path(__file__).parent.parent / 'sample.json'

SAMPLE_PKG_IMPORTS = [
    ('foo.__init__', []),
    ('foo.a', ['foo.b']),
    ('foo.b', []),
]


def module_imports(results):
    return [(res['module'], res['imports']) for res in results]


def embedded_results(html):
    """Extract the results JSON embedded by format_html()"""
    start = html.index('const results = ') + len('const results = ')
    end = html.index(';\n', start)
    return json.loads(html[start:end])


class TestRunImportDeps(unittest.TestCase):
    def test_package(self):
        results = run_import_deps([str(SAMPLE_PKG)])
        self.assertEqual(module_imports(results), SAMPLE_PKG_IMPORTS)

    def test_invalid_path(self):
        with self.assertRaises(SystemExit) as ctx:
            run_import_deps(['/no/such/path'])
        self.assertEqual(ctx.exception.code, 1)


class TestEncodeFragmentSlim(unittest.TestCase):
    def test_only_module_and_imports(self):
        results = [{'module': 'foo.a', 'filepath': '/home/me/foo/a.py', 'imports': ['foo.b']}]
        slim = [{'module': 'foo.a', 'imports': ['foo.b']}]
        self.assertEqual(encode_fragment(results), encode_fragment(slim))


class TestFormatHtmlSlim(unittest.TestCase):
    def test_no_local_paths(self):
        results = [{'module': 'foo.a', 'filepath': '/home/me/foo/a.py', 'imports': ['foo.b']}]
        html = format_html(results)
        self.assertNotIn('/home/me', html)
        self.assertEqual(embedded_results(html), [{'module': 'foo.a', 'imports': ['foo.b']}])


class TestViewerUrl(unittest.TestCase):
    def test_url(self):
        results = json.loads(SAMPLE_JSON.read_text())
        url = viewer_url('https://example.org/view', results)
        self.assertEqual(url, 'https://example.org/view#' + encode_fragment(results))

    def test_too_long(self):
        results = json.loads(SAMPLE_JSON.read_text())
        self.assertIsNone(viewer_url('https://example.org/view', results, max_length=50))


class TestMain(unittest.TestCase):
    def setUp(self):
        self.tmp_dir = tempfile.TemporaryDirectory()
        self.out_path = pathlib.Path(self.tmp_dir.name) / 'deps.html'

    def tearDown(self):
        self.tmp_dir.cleanup()

    def test_output_file(self):
        main([str(SAMPLE_PKG), '-o', str(self.out_path)])
        results = embedded_results(self.out_path.read_text())
        self.assertEqual(module_imports(results), SAMPLE_PKG_IMPORTS)

    def test_output_stdout(self):
        stdout = io.StringIO()
        with contextlib.redirect_stdout(stdout):
            main([str(SAMPLE_PKG), '-o', '-'])
        results = embedded_results(stdout.getvalue())
        self.assertEqual(module_imports(results), SAMPLE_PKG_IMPORTS)

    def test_json_from_stdin(self):
        with mock.patch('sys.stdin', io.StringIO(SAMPLE_JSON.read_text())):
            main(['-o', str(self.out_path)])
        results = embedded_results(self.out_path.read_text())
        self.assertEqual(results, json.loads(SAMPLE_JSON.read_text()))

    def test_open_local_file(self):
        with mock.patch('webbrowser.open') as browser_open:
            main([str(SAMPLE_PKG)])
        url = browser_open.call_args.args[0]
        self.assertEqual(urlparse(url).scheme, 'file')
        html_path = pathlib.Path(url2pathname(urlparse(url).path))
        results = embedded_results(html_path.read_text())
        html_path.unlink()
        self.assertEqual(module_imports(results), SAMPLE_PKG_IMPORTS)

    def test_open_viewer(self):
        with mock.patch('webbrowser.open') as browser_open:
            main([str(SAMPLE_PKG), '--viewer', 'https://example.org/'])
        url = browser_open.call_args.args[0]
        self.assertTrue(url.startswith('https://example.org/#d='))

    def test_open_viewer_too_long_falls_back_to_file(self):
        with mock.patch('webbrowser.open') as browser_open:
            with mock.patch.object(deps_viz, 'MAX_URL_LENGTH', 50):
                main([str(SAMPLE_PKG), '--viewer', 'https://example.org/'])
        url = browser_open.call_args.args[0]
        self.assertEqual(urlparse(url).scheme, 'file')
        pathlib.Path(url2pathname(urlparse(url).path)).unlink()
