"""An offline stand-in for books.toscrape.com: 3 catalogue pages x 20 books, built from the real page markup.
Tests never touch the network."""
from pathlib import Path

FIX = Path(__file__).parent / "fixtures"
BASE = "https://books.toscrape.com/catalogue/"
RATINGS = ["One", "Two", "Three", "Four", "Five"]


def slug(n: int) -> str:
    return f"book-number-{n}_{1000 - n}"


POD = """<article class="product_pod">
  <div class="image_container"><a href="{slug}/index.html"><img src="../media/x.jpg" alt="Book {n}" class="thumbnail"></a></div>
  <p class="star-rating {rating}"><i class="icon-star"></i></p>
  <h3><a href="{slug}/index.html" title="Book {n}">Book {n}...</a></h3>
  <div class="product_price"><p class="price_color">£{price}</p><p class="instock availability"><i class="icon-ok"></i> In stock</p></div>
</article>"""


def catalogue(page: int) -> str:
    pods = "\n".join(POD.format(slug=slug(n), n=n, rating=RATINGS[n % 5], price=f"{10 + n}.99")
                     for n in range((page - 1) * 20 + 1, page * 20 + 1))
    nxt = f'<li class="next"><a href="page-{page + 1}.html">next</a></li>'
    return f'<html><body><ol class="row">{pods}</ol><ul class="pager"><li class="current">Page {page} of 50</li>{nxt}</ul></body></html>'


def detail(n: int) -> str:
    html = (FIX / "book-a-light-in-the-attic.html").read_text(encoding="utf-8")
    return (html.replace("A Light in the Attic", f"Book {n}").replace("£51.77", f"£{10 + n}.99")
                .replace("star-rating Three", f"star-rating {RATINGS[n % 5]}"))


class Resp:
    def __init__(self, status: int, text: str = ""):
        self.status_code, self.text, self.encoding = status, text, None


class FakeSession:
    """requests.Session look-alike. `script` can force statuses per URL, e.g. {url: [503, 200]}."""

    def __init__(self, script: dict | None = None):
        self.headers, self.calls, self.script = {}, [], {k: list(v) for k, v in (script or {}).items()}

    def get(self, url, timeout=None):
        assert timeout, "every request must have a timeout"
        self.calls.append(url)
        if url in self.script and self.script[url]:
            status = self.script[url].pop(0)
            if status != 200:
                return Resp(status)
        if url.startswith(BASE + "page-"):
            return Resp(200, catalogue(int(url.split("page-")[1].split(".")[0])))
        for n in range(1, 61):
            if url == f"{BASE}{slug(n)}/index.html":
                return Resp(200, detail(n))
        return Resp(404, "Not found")
