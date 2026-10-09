"""Regression checks for generated metadata, crawl routes and accessible links."""
from html.parser import HTMLParser
from pathlib import Path
from urllib.parse import urlsplit, urljoin
import importlib.util
import json
import tempfile
import unittest
import xml.etree.ElementTree as ET

ROOT = Path(__file__).resolve().parents[1]
CONFIG = json.loads((ROOT / 'site.json').read_text())
BASE = CONFIG['url'].rstrip('/') + '/'


class Document(HTMLParser):
    def __init__(self, path):
        super().__init__()
        self.meta, self.links, self.ids, self.scripts, self.resources = {}, [], [], [], []
        self.title = ''
        self._title, self._schema, self._json = False, False, ''
        self.feed(path.read_text())

    def handle_starttag(self, tag, attrs):
        attrs = dict(attrs)
        if 'id' in attrs:
            self.ids.append(attrs['id'])
        if tag == 'meta':
            key = attrs.get('name', attrs.get('property', ''))
            self.meta.setdefault(key, []).append(attrs.get('content', ''))
        if tag in ('link', 'a'):
            self.links.append(attrs)
        if tag == 'title':
            self._title = True
        if tag == 'script':
            self._schema = attrs.get('type') == 'application/ld+json'
            self._json = ''
        if tag in ('script', 'img') and 'src' in attrs:
            self.resources.append(attrs['src'])

    def handle_data(self, data):
        if self._title:
            self.title += data
        if self._schema:
            self._json += data

    def handle_endtag(self, tag):
        if tag == 'title':
            self._title = False
        if tag == 'script' and self._schema:
            self.scripts.append(json.loads(self._json))
            self._schema = False


class SearchAndNavigationTests(unittest.TestCase):
    def test_titles_descriptions_and_share_urls_match_each_page(self):
        titles, descriptions = [], []
        for info in CONFIG['pages']:
            page = Document(ROOT / info['file'])
            canonical = BASE + ('' if info['file'] == 'index.html' else info['file'])
            self.assertEqual(page.title, info['title'])
            self.assertEqual(page.meta['description'], [info['description']])
            self.assertEqual([link['href'] for link in page.links if link.get('rel') == 'canonical'], [canonical])
            self.assertEqual(page.meta['og:url'], [canonical])
            for key in ('og:title', 'twitter:title'):
                self.assertEqual(page.meta[key], [info['title']])
            for key in ('og:description', 'twitter:description'):
                self.assertEqual(page.meta[key], [info['description']])
            self.assertNotIn('noindex', page.meta['robots'][0])
            self.assertTrue((ROOT / page.meta['og:image'][0].removeprefix(BASE)).is_file())
            titles.append(page.title)
            descriptions.append(page.meta['description'][0])
        self.assertEqual(len(set(titles)), len(titles))
        self.assertEqual(len(set(descriptions)), len(descriptions))

    def test_sitemap_exactly_matches_canonical_pages(self):
        tree = ET.parse(ROOT / 'sitemap.xml')
        locations = [node.text for node in tree.findall('.//{*}loc')]
        expected = [BASE + ('' if page['file'] == 'index.html' else page['file']) for page in CONFIG['pages']]
        self.assertCountEqual(locations, expected)
        self.assertEqual(len(locations), len(set(locations)))
        self.assertNotIn(BASE + '404.html', locations)
        self.assertIn('noindex', Document(ROOT / '404.html').meta['robots'][0])

    def test_structured_data_is_valid_and_has_no_unsubstantiated_reviews(self):
        for info in CONFIG['pages']:
            page = Document(ROOT / info['file'])
            self.assertEqual(len(page.scripts), 1)
            data = page.scripts[0]
            self.assertEqual(data['@context'], 'https://schema.org')
            nodes = {node['@type']: node for node in data['@graph']}
            self.assertEqual(nodes['WebSite']['name'], CONFIG['name'])
            self.assertEqual(nodes['WebSite']['url'], BASE)
            self.assertEqual(nodes['Organization']['email'], CONFIG['email'])
            self.assertEqual(nodes['WebPage']['description'], info['description'])
            self.assertNotIn('aggregateRating', json.dumps(data))
            self.assertNotIn('reviewRating', json.dumps(data))
            if info['file'] == 'index.html':
                self.assertEqual(nodes['SoftwareApplication']['downloadUrl'], CONFIG['app_store_url'])

    def test_every_fragment_and_script_resolves_and_ids_are_unique(self):
        pages = {path.name: Document(path) for path in ROOT.glob('*.html')}
        for name, page in pages.items():
            self.assertEqual(len(page.ids), len(set(page.ids)), name)
            for href in [link.get('href', '') for link in page.links] + page.resources:
                target = urlsplit(href)
                if target.scheme or target.netloc:
                    continue
                if target.path:
                    self.assertTrue((ROOT / target.path).is_file(), (name, href))
                if target.fragment:
                    destination = pages.get(target.path or name)
                    self.assertIsNotNone(destination, (name, href))
                    self.assertIn(target.fragment, destination.ids, (name, href))

    def test_manifest_works_on_both_preview_and_hosted_subpath(self):
        manifest = json.loads((ROOT / 'site.webmanifest').read_text())
        self.assertEqual(manifest['name'], CONFIG['name'])
        for base in (BASE, 'http://127.0.0.1:8766/'):
            for field in ('id', 'start_url', 'scope'):
                self.assertEqual(urljoin(base + 'site.webmanifest', manifest[field]), base)
        for icon in manifest['icons']:
            self.assertTrue((ROOT / icon['src']).is_file())

    def test_missing_nested_urls_have_working_assets_and_same_page_skip_link(self):
        page = Document(ROOT / '404.html')
        self.assertNotIn('<base', (ROOT / '404.html').read_text())
        self.assertIn('#main', [link.get('href') for link in page.links])
        self.assertIn('main', page.ids)
        for href in [link.get('href', '') for link in page.links] + page.resources:
            self.assertTrue(href.startswith(('https://', '#')), href)

    def test_checked_in_output_matches_a_fresh_build(self):
        spec = importlib.util.spec_from_file_location('site_builder', ROOT / 'scripts/build.py')
        builder = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(builder)
        with tempfile.TemporaryDirectory() as folder:
            output = Path(folder)
            (output / 'content').mkdir()
            for path in (ROOT / 'content').glob('*.html'):
                (output / 'content' / path.name).write_bytes(path.read_bytes())
            (output / 'site.json').write_bytes((ROOT / 'site.json').read_bytes())
            builder.ROOT = output
            builder.render_all()
            for generated in output.iterdir():
                if generated.is_file() and generated.name != 'site.json':
                    self.assertEqual(generated.read_bytes(), (ROOT / generated.name).read_bytes(), generated.name)


if __name__ == '__main__':
    unittest.main()
