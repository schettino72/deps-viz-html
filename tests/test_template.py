import json
import pathlib

import pytest
from playwright.sync_api import sync_playwright

from deps_viz import detect_cycles, format_html


SAMPLE = pathlib.Path(__file__).parent.parent / 'sample.json'

CYCLE_DATA = [
    {"module": "pkg.a", "imports": ["pkg.b"]},
    {"module": "pkg.b", "imports": ["pkg.c"]},
    {"module": "pkg.c", "imports": ["pkg.a"]},
    {"module": "pkg.d", "imports": ["pkg.a"]},
]


@pytest.fixture(scope='module')
def browser():
    with sync_playwright() as pw:
        browser = pw.chromium.launch()
        yield browser
        browser.close()


@pytest.fixture
def open_graph(browser, tmp_path):
    """Generate HTML for given results, open it, return (page, errors)"""
    pages = []

    def _open(results):
        html_path = tmp_path / 'deps.html'
        html_path.write_text(format_html(results, detect_cycles(results)))
        page = browser.new_page()
        pages.append(page)
        errors = []
        page.on('pageerror', lambda exc: errors.append(str(exc)))
        page.goto(html_path.as_uri())
        page.wait_for_function('typeof cy !== "undefined" && cy.nodes().length > 0')
        return page, errors

    yield _open
    for page in pages:
        page.close()


def test_render_sample(open_graph):
    results = json.loads(SAMPLE.read_text())
    page, errors = open_graph(results)
    assert errors == []
    assert page.evaluate('cy.nodes().length') == len(results)
    num_links = sum(len(res['imports']) for res in results)
    assert page.evaluate('cy.edges().length') == num_links


@pytest.mark.parametrize('layout', ['dagre-lr', 'dagre-tb', 'cose'])
def test_layouts(open_graph, layout):
    page, errors = open_graph(json.loads(SAMPLE.read_text()))
    page.select_option('#layout-select', layout)
    page.wait_for_timeout(500)
    assert errors == []
    # layout positioned nodes: not all at the same point
    positions = page.evaluate('cy.nodes().map(n => [n.position("x"), n.position("y")])')
    assert len({tuple(pos) for pos in positions}) == len(positions)


def test_cycle_edges(open_graph):
    page, errors = open_graph(CYCLE_DATA)
    assert errors == []
    cycle_edges = page.evaluate('cy.edges(".cycle").map(e => e.id()).sort()')
    assert cycle_edges == ['pkg.a->pkg.b', 'pkg.b->pkg.c', 'pkg.c->pkg.a']
