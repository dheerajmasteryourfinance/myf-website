"""SEO build: page titles/descriptions/share tags + a plain-HTML copy of each page's content.

Run after content changes (needs Playwright + Chromium):
    python3 -m http.server 8765        # in the repo folder, separate terminal
    python3 scripts/build_seo.py

What it does for each entry page (index, services, industries, tools, about, book):
  1. Writes the <head> SEO block between <!--seo:start--> and <!--seo:end-->.
  2. Renders the page in a browser and saves the finished HTML inside #app between
     <!--prerender:start--> and <!--prerender:end-->. Search engines, link previews and
     visitors without JavaScript read this copy; with JavaScript the live page replaces it.
Re-running replaces both blocks, so it is safe to run any number of times.
"""
import json, os, re, sys
from playwright.sync_api import sync_playwright

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
SITE = 'https://masteryourfinance.org'
LOCAL = sys.argv[1] if len(sys.argv) > 1 else 'http://localhost:8765'
IMG = f'{SITE}/assets/og-image.png'

PAGES = {
    'index.html': ('Master Your Finance | Outsourced finance team for professional service firms',
                   'Reliable finance professionals delivering bookkeeping, monthly reporting, cash flow forecasting and CFO-lite support for growing firms in the US, UK and Australia.'),
    'services.html': ('Finance services: bookkeeping, reporting & cash flow | Master Your Finance',
                      'Bookkeeping and accounting, monthly reporting, cash flow forecasting, CFO-lite support and finance operations for professional service firms. See what is included in each service.'),
    'industries.html': ('Industries: law firms, agencies & consultancies | Master Your Finance',
                        'Outsourced finance for law firms, marketing and creative agencies, IT and consulting firms, other professional services and startups, with the KPIs that matter to each.'),
    'tools.html': ('Free finance tools for professional service firms | Master Your Finance',
                   'Free tools for firms that sell expertise: Financial GPS snapshot, law firm health check, utilisation and DSO self-diagnostic, cash flow runway estimator and a 30-day sprint planner.'),
    'about-us.html': ('About us | Master Your Finance',
                   'Meet the team behind Master Your Finance, the extended finance team and Financial GPS for small and mid-sized professional service firms in the US, UK and Australia.'),
    'contact-us.html': ('Book a free 30-minute finance review | Master Your Finance',
                  'Book a free 30-minute finance review with Master Your Finance. Tell us about your firm and we come back with the two or three things worth fixing first.'),
}
ORG = {
    '@context': 'https://schema.org', '@type': 'ProfessionalService', 'name': 'Master Your Finance',
    'url': SITE + '/', 'logo': SITE + '/assets/logo-green.svg', 'image': IMG,
    'description': PAGES['index.html'][1], 'areaServed': ['United States', 'United Kingdom', 'Australia'],
    'serviceType': ['Bookkeeping', 'Monthly financial reporting', 'Cash flow forecasting', 'Outsourced CFO support', 'Finance operations'],
}


def esc(s):
    return s.replace('&', '&amp;').replace('"', '&quot;').replace('<', '&lt;')


def seo_block(page, title, desc):
    url = SITE + '/' + ('' if page == 'index.html' else page[:-5])   # clean URLs: /services, /about-us ...
    out = [
        '<!--seo:start-->',
        f'<title>{esc(title)}</title>',
        f'<meta name="description" content="{esc(desc)}">',
        f'<link rel="canonical" href="{url}">',
        '<meta property="og:type" content="website">',
        '<meta property="og:site_name" content="Master Your Finance">',
        f'<meta property="og:title" content="{esc(title)}">',
        f'<meta property="og:description" content="{esc(desc)}">',
        f'<meta property="og:url" content="{url}">',
        f'<meta property="og:image" content="{IMG}">',
        '<meta property="og:image:width" content="1200"><meta property="og:image:height" content="630">',
        '<meta property="og:image:alt" content="Master Your Finance: your outsourced finance team">',
        '<meta name="twitter:card" content="summary_large_image">',
        f'<meta name="twitter:title" content="{esc(title)}">',
        f'<meta name="twitter:description" content="{esc(desc)}">',
        f'<meta name="twitter:image" content="{IMG}">',
    ]
    if page == 'index.html':
        out.append('<script type="application/ld+json">' + json.dumps(ORG) + '</script>')
    out.append('<!--seo:end-->')
    return '\n'.join(out)


def put_seo(s, block):
    if '<!--seo:start-->' in s:
        return re.sub(r'<!--seo:start-->.*?<!--seo:end-->', lambda m: block, s, flags=re.S)
    s = re.sub(r'<title>[^<]*</title>\n?', '', s, 1)
    s = re.sub(r'<meta name="description"[^>]*>\n?', '', s, 1)
    return re.sub(r"(<meta name=\"viewport\"[^>]*>)", lambda m: m.group(1) + "\n" + block, s, count=1)


JS_FLAG = "<script>document.documentElement.className+=' js'</script>"
PRE_CSS = ('/* Plain-HTML copy of the page (for search engines and no-JavaScript visitors); hidden once JavaScript runs */\n'
           '.js #app > .pre{display:none}\nhtml:not(.js) #app > .boot{display:none}\n')


def clean(html):
    html = re.sub(r'class="myf([^"]*)"', lambda m: 'class="myf' + m.group(1).replace('rv-ready', '') + '"', html, 1)
    html = re.sub(r'class="rsec\b([^"]*)"', lambda m: 'class="' + ' '.join(['rsec', 'in'] + [c for c in m.group(1).split() if c != 'in']) + '"', html)
    html = html.replace(' data-off=""', '')
    html = re.sub(r'\n{3,}', '\n\n', html)
    return html.strip()


def put_pre(s, html):
    block = f'<!--prerender:start--><div class="pre">\n{html}\n</div><!--prerender:end-->'
    if '<!--prerender:start-->' in s:
        s = re.sub(r'<!--prerender:start-->.*?<!--prerender:end-->', lambda m: block, s, flags=re.S)
    else:
        s = s.replace('<div id="app"><div class="boot">Loading…</div></div>',
                      '<div id="app"><div class="boot">Loading…</div>' + block + '</div>', 1)
    s = re.sub(r'<noscript>.*?</noscript>\n?', '', s, flags=re.S)
    if JS_FLAG not in s:
        s = s.replace('<link rel="stylesheet" href="myf.css">', '<link rel="stylesheet" href="myf.css">\n' + JS_FLAG, 1)
    if '.js #app > .pre' not in s:
        s = s.replace('.boot{', PRE_CSS + '.boot{', 1)
    return s


def main():
    with sync_playwright() as p:
        b = p.chromium.launch(executable_path=os.environ.get('CHROMIUM', '/opt/pw-browsers/chromium'))
        pg = b.new_page(viewport={'width': 1366, 'height': 900})
        for page, (title, desc) in PAGES.items():
            path = os.path.join(ROOT, page)
            s = open(path, encoding='utf-8').read()
            pg.goto(f'{LOCAL}/{page}')
            pg.wait_for_function("document.querySelector('#app > .myf') !== null", timeout=20000)
            pg.wait_for_timeout(4000)
            html = clean(pg.evaluate("document.querySelector('#app > .myf').outerHTML"))
            s = put_pre(put_seo(s, seo_block(page, title, desc)), html)
            open(path, 'w', encoding='utf-8').write(s)
            words = len(re.sub(r'<[^>]+>', ' ', html).split())
            print(f'{page}: {words} words of plain HTML')
        b.close()

    hc = os.path.join(ROOT, 'health-check.html')
    s = open(hc, encoding='utf-8').read()
    t = re.search(r'<title>([^<]*)</title>', s).group(1)
    d = re.search(r'<meta name="description" content="([^"]*)"', s).group(1)
    s = put_seo(s, seo_block('health-check.html', t.replace('&amp;', '&'), d.replace('&amp;', '&')))
    open(hc, 'w', encoding='utf-8').write(s)

    urls = [SITE + '/'] + [f'{SITE}/{p[:-5]}' for p in PAGES if p != 'index.html'] + [f'{SITE}/health-check']
    open(os.path.join(ROOT, 'sitemap.xml'), 'w').write(
        '<?xml version="1.0" encoding="UTF-8"?>\n<urlset xmlns="http://www.sitemaps.org/schemas/sitemap/0.9">\n'
        + ''.join(f'  <url><loc>{u}</loc></url>\n' for u in urls) + '</urlset>\n')
    open(os.path.join(ROOT, 'robots.txt'), 'w').write(f'User-agent: *\nAllow: /\nDisallow: /scripts/\nDisallow: /api/\n\nSitemap: {SITE}/sitemap.xml\n')
    print('health-check.html, sitemap.xml, robots.txt updated')


if __name__ == '__main__':
    main()
