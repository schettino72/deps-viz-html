import base64
import json
import pathlib
import tempfile
import unittest
import zlib

from playwright.sync_api import sync_playwright

from deps_viz import encode_fragment, format_html


SAMPLE = pathlib.Path(__file__).parent.parent / 'sample.json'
TEMPLATE = pathlib.Path(__file__).parent.parent / 'deps_viz' / 'template.html'

GRAPH_READY = 'typeof cy !== "undefined" && cy !== null && cy.nodes().length > 0'

CYCLE_DATA = [
    {"module": "pkg.a", "imports": ["pkg.b"]},
    {"module": "pkg.b", "imports": ["pkg.c"]},
    {"module": "pkg.c", "imports": ["pkg.a"]},
    {"module": "pkg.d", "imports": ["pkg.a"]},
]

OTHER_DATA = [
    {"module": "other.x", "imports": ["other.y"]},
    {"module": "other.y", "imports": []},
]

# imports of modules not in the list (stdlib, 3rd party) are ignored
EXTERNAL_IMPORT_DATA = [
    {"module": "pkg.a", "imports": ["pkg.b", "os.path", "requests"]},
    {"module": "pkg.b", "imports": []},
]

# names with HTML must be rendered as text, never as markup
HTML_NAME_DATA = [
    {"module": "pk<b>g.mod", "imports": []},
]

# a->c->b->a is a cycle reached through a DFS cross edge (c->b)
CROSS_CYCLE_DATA = [
    {"module": "pkg.a", "imports": ["pkg.b", "pkg.c"]},
    {"module": "pkg.b", "imports": ["pkg.a"]},
    {"module": "pkg.c", "imports": ["pkg.b"]},
]


class BrowserTestCase(unittest.TestCase):
    """Shared headless browser; each test gets a fresh page"""

    @classmethod
    def setUpClass(cls):
        cls.pw = sync_playwright().start()
        cls.browser = cls.pw.chromium.launch()

    @classmethod
    def tearDownClass(cls):
        cls.browser.close()
        cls.pw.stop()

    def setUp(self):
        self.tmp_dir = tempfile.TemporaryDirectory()
        self.page = self.browser.new_page()
        self.errors = []
        self.page.on('pageerror', lambda exc: self.errors.append(str(exc)))

    def tearDown(self):
        self.page.close()
        self.tmp_dir.cleanup()

    def open_graph(self, results, name='deps.html'):
        html_path = pathlib.Path(self.tmp_dir.name) / name
        html_path.write_text(format_html(results))
        self.page.goto(html_path.as_uri())
        self.page.wait_for_function(GRAPH_READY)

    def node_positions(self):
        positions = self.page.evaluate('cy.nodes().map(n => [n.position("x"), n.position("y")])')
        return {tuple(pos) for pos in positions}


class TestRender(BrowserTestCase):
    def test_sample(self):
        self.open_graph(json.loads(SAMPLE.read_text()))
        self.assertEqual(self.errors, [])
        self.assertEqual(self.page.evaluate('cy.nodes().length'), 7)
        self.assertEqual(self.page.evaluate('cy.edges().length'), 5)

    def test_external_imports_ignored(self):
        self.open_graph(EXTERNAL_IMPORT_DATA)
        self.assertEqual(self.errors, [])
        self.assertEqual(self.page.evaluate('cy.nodes().map(n => n.id()).sort()'), ['pkg.a', 'pkg.b'])
        self.assertEqual(self.page.evaluate('cy.edges().map(e => e.id())'), ['pkg.a->pkg.b'])

    def test_cycle_edges(self):
        self.open_graph(CYCLE_DATA)
        self.assertEqual(self.errors, [])
        cycle_edges = self.page.evaluate('cy.edges(".cycle").map(e => e.id()).sort()')
        self.assertEqual(cycle_edges, ['pkg.a->pkg.b', 'pkg.b->pkg.c', 'pkg.c->pkg.a'])

    def test_cycle_cross_edge(self):
        self.open_graph(CROSS_CYCLE_DATA)
        self.assertEqual(self.errors, [])
        cycle_edges = self.page.evaluate('cy.edges(".cycle").map(e => e.id()).sort()')
        expected = ['pkg.a->pkg.b', 'pkg.a->pkg.c', 'pkg.b->pkg.a', 'pkg.c->pkg.b']
        self.assertEqual(cycle_edges, expected)


class TestLayouts(BrowserTestCase):
    """After layout, every node has a distinct position"""

    def test_dagre_lr(self):
        self.open_graph(json.loads(SAMPLE.read_text()))
        self.page.select_option('#layout-select', 'dagre-lr')
        self.page.wait_for_timeout(500)
        self.assertEqual(self.errors, [])
        self.assertEqual(len(self.node_positions()), 7)

    def test_dagre_tb(self):
        self.open_graph(json.loads(SAMPLE.read_text()))
        self.page.select_option('#layout-select', 'dagre-tb')
        self.page.wait_for_timeout(500)
        self.assertEqual(self.errors, [])
        self.assertEqual(len(self.node_positions()), 7)

    def test_cose(self):
        self.open_graph(json.loads(SAMPLE.read_text()))
        self.page.select_option('#layout-select', 'cose')
        self.page.wait_for_timeout(500)
        self.assertEqual(self.errors, [])
        self.assertEqual(len(self.node_positions()), 7)


class TestEscaping(BrowserTestCase):
    def test_package_name_is_text(self):
        self.open_graph(HTML_NAME_DATA)
        self.assertEqual(self.errors, [])
        self.assertEqual(self.page.locator('#package-filters b').count(), 0)
        self.assertIn('pk<b>g', self.page.inner_text('#package-filters'))

    def test_removed_node_is_text(self):
        self.open_graph(HTML_NAME_DATA)
        self.page.evaluate('removeNode("pk<b>g.mod")')
        self.assertEqual(self.page.locator('#removed-nodes b').count(), 0)
        self.assertIn('pk<b>g.mod', self.page.inner_text('#removed-nodes'))


class TestStoragePerDataset(BrowserTestCase):
    """Removed nodes are remembered per dataset, not shared between projects"""

    def test_removed_nodes_not_shared(self):
        self.open_graph(json.loads(SAMPLE.read_text()), name='a.html')
        self.page.evaluate('removeNode("foo.foo_a")')
        self.open_graph(OTHER_DATA, name='b.html')
        self.assertEqual(self.page.evaluate('removedNodeIds.size'), 0)
        self.assertEqual(self.page.evaluate('cy.nodes().length'), 2)

    def test_removed_nodes_restored_for_same_dataset(self):
        self.open_graph(json.loads(SAMPLE.read_text()), name='a.html')
        self.page.evaluate('removeNode("foo.foo_a")')
        self.page.reload()
        self.page.wait_for_function(GRAPH_READY)
        self.assertEqual(self.page.evaluate('[...removedNodeIds]'), ['foo.foo_a'])
        self.assertEqual(self.page.evaluate('cy.nodes().length'), 6)


class TestEncodeFragment(unittest.TestCase):
    def test_roundtrip(self):
        results = json.loads(SAMPLE.read_text())
        fragment = encode_fragment(results)
        self.assertTrue(fragment.startswith('d='))
        packed = base64.urlsafe_b64decode(fragment[2:] + '=' * (-len(fragment[2:]) % 4))
        self.assertEqual(json.loads(zlib.decompress(packed, wbits=-15)), results)

    def test_url_safe(self):
        fragment = encode_fragment(json.loads(SAMPLE.read_text()))
        self.assertNotRegex(fragment[2:], r'[^A-Za-z0-9_-]')


class TestHostedViewer(BrowserTestCase):
    """Template without embedded data: loads from URL fragment or file"""

    def test_load_from_fragment(self):
        fragment = encode_fragment(json.loads(SAMPLE.read_text()))
        self.page.goto(TEMPLATE.as_uri() + '#' + fragment)
        self.page.wait_for_function(GRAPH_READY)
        self.assertEqual(self.errors, [])
        self.assertEqual(self.page.evaluate('cy.nodes().length'), 7)

    def test_empty_state(self):
        self.page.goto(TEMPLATE.as_uri())
        self.page.wait_for_selector('#empty-state', state='visible')
        self.assertEqual(self.errors, [])

    def test_load_from_file(self):
        self.page.goto(TEMPLATE.as_uri())
        self.page.set_input_files('#file-input', str(SAMPLE))
        self.page.wait_for_function(GRAPH_READY)
        self.assertEqual(self.errors, [])
        self.assertEqual(self.page.evaluate('cy.nodes().length'), 7)
        self.assertFalse(self.page.is_visible('#empty-state'))
