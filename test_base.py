from sources.base import Source

# This should fail — can't instantiate ABC
try:
    s = Source()
    print("FAIL: should have raised TypeError")
except TypeError:
    print("PASS: Source is abstract")

# Define a minimal subclass
class TestSource(Source):
    @property
    def name(self): return "test"
    @property
    def label(self): return "Test"
    @property
    def browse_urls(self): return {"latest": "http://test.com"}
    def fetch_url(self, url, params=None): pass
    def extract_novel_rows(self, soup): return []
    def search(self, query, page=1): return ([], 0)
    def fetch_chapters(self, slug): return []
    def read_chapter(self, url): return None
    def save_chapter(self, url, title, slug): return False
    def parse_slug(self, url): return None
    def qualify_slug(self, slug): return f"test:{slug}"
    def cover_url(self, slug): return ""

# This should work
t = TestSource()
print(f"PASS: TestSource instantiated, name={t.name}")
