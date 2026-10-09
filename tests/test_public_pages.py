"""Check public navigation, assets, brand and support routing without network access."""
from html.parser import HTMLParser
from pathlib import Path
from urllib.parse import urlsplit
import unittest

ROOT = Path(__file__).resolve().parents[1]


class Page(HTMLParser):
    def __init__(self, path):
        super().__init__()
        self.links = []
        self.images = []
        self.headings = 0
        self.feed(path.read_text())

    def handle_starttag(self, tag, attrs):
        attrs = dict(attrs)
        if tag in ("a", "link") and attrs.get("href"):
            self.links.append(attrs["href"])
        if tag == "img":
            self.images.append(attrs)
        if tag == "h1":
            self.headings += 1


class PublicPagesTests(unittest.TestCase):
    def test_all_local_navigation_and_assets_resolve(self):
        for path in ROOT.glob("*.html"):
            page = Page(path)
            for reference in page.links + [image["src"] for image in page.images]:
                target = urlsplit(reference)
                if not target.scheme and target.path:
                    self.assertTrue((path.parent / target.path).is_file(), (path.name, reference))
            self.assertEqual(page.headings, 1, path.name)
            self.assertTrue(all("alt" in image for image in page.images), path.name)

    def test_help_and_legal_pages_use_only_confirmed_mailbox(self):
        for name in ("support.html", "privacy.html", "terms.html"):
            mailboxes = [href for href in Page(ROOT / name).links if href.startswith("mailto:")]
            self.assertEqual(mailboxes, ["mailto:nayproductionshq@gmail.com"], name)

    def test_pages_do_not_publish_disputed_name_or_domain(self):
        for path in ROOT.glob("*.html"):
            self.assertNotIn("sitemate", path.read_text().lower(), path.name)
            self.assertIn("Days &amp; Dues", path.read_text(), path.name)

    def test_public_help_navigation_remains_available(self):
        self.assertTrue({"support.html", "privacy.html", "terms.html"}.issubset(Page(ROOT / "index.html").links))
        self.assertTrue(all("index.html" in Page(ROOT / name).links for name in ("support.html", "privacy.html", "terms.html")))


if __name__ == "__main__":
    unittest.main()
