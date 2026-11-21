import json
import pathlib
import tempfile
import unittest

from playwright.sync_api import sync_playwright

from deps_viz import format_html


SAMPLE = pathlib.Path(__file__).parent.parent / 'sample.json'

CYCLE_DATA = [
    {"module": "pkg.a", "imports": ["pkg.b"]},
    {"module": "pkg.b", "imports": ["pkg.c"]},
    {"module": "pkg.c", "imports": ["pkg.a"]},
    {"module": "pkg.d", "imports": ["pkg.a"]},
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

    def open_graph(self, results):
        html_path = pathlib.Path(self.tmp_dir.name) / 'deps.html'
        html_path.write_text(format_html(results))
        self.page.goto(html_path.as_uri())
        self.page.wait_for_function('typeof cy !== "undefined" && cy.nodes().length > 0')

    def node_positions(self):
        positions = self.page.evaluate('cy.nodes().map(n => [n.position("x"), n.position("y")])')
        return {tuple(pos) for pos in positions}


class TestRender(BrowserTestCase):
    def test_sample(self):
        self.open_graph(json.loads(SAMPLE.read_text()))
        self.assertEqual(self.errors, [])
        self.assertEqual(self.page.evaluate('cy.nodes().length'), 7)
        self.assertEqual(self.page.evaluate('cy.edges().length'), 5)

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
