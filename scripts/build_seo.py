"""SEO + agent build: page tags, structured data, plain-HTML copies, Markdown copies, llms.txt, sitemap, robots.txt.

Run after content changes (needs Playwright + Chromium, and `pip install markdownify`):
    python3 -m http.server 8765        # in the repo folder, separate terminal
    python3 scripts/build_seo.py

For each entry page it:
  1. Writes the <head> SEO block (title, description, share tags, JSON-LD structured data,
     Markdown alternate link, WebMCP script) between <!--seo:start--> and <!--seo:end-->.
  2. Renders the page in a browser and saves the finished HTML inside #app between
     <!--prerender:start--> and <!--prerender:end--> (for search engines and no-JS visitors).
  3. Saves a Markdown copy next to it (index.md, services.md, ...) for AI agents.
It also writes llms.txt, sitemap.xml (with lastmod dates) and robots.txt (with Content-Signal).
Re-running replaces everything it wrote, so it is safe to run any number of times.
"""
import datetime, json, os, re, subprocess, sys
from playwright.sync_api import sync_playwright
from markdownify import markdownify

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
SITE = 'https://masteryourfinance.org'
LOCAL = sys.argv[1] if len(sys.argv) > 1 else 'http://localhost:8765'
IMG = f'{SITE}/assets/og-image.png'
EMAIL = 'himanshu@masteryourbusiness.org'
CALENDLY = 'https://calendly.com/himanshu-masteryourbusiness/30-minutes-discovery-call-law-firms'

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
    'privacy-policy.html': ('Privacy policy | Master Your Finance',
                            'How Master Your Finance collects, uses and protects personal data from its website, contact form and free health check.'),
    'terms.html': ('Terms of use | Master Your Finance',
                   'Terms for using the Master Your Finance website and its free finance tools, including the health check.'),
    'contact-us.html': ('Book a free 30-minute finance review | Master Your Finance',
                        'Book a free 30-minute finance review with Master Your Finance. Tell us about your firm and we come back with the two or three things worth fixing first.'),
}
NAMES = {'index.html': 'Home', 'services.html': 'Services', 'industries.html': 'Industries', 'tools.html': 'Tools & Resources',
         'about-us.html': 'About us', 'privacy-policy.html': 'Privacy policy', 'terms.html': 'Terms of use',
         'contact-us.html': 'Contact us', 'health-check.html': 'Law firm health check'}
PAGE_TYPE = {'about-us.html': 'AboutPage', 'contact-us.html': 'ContactPage'}

SERVICES = [
    ('Bookkeeping & Accounting', 'bookkeeping', 'Clean books, reconciled accounts, and AR/AP handled every week.'),
    ('Cash Flow Forecasting', 'cash-flow', 'See what is coming in and going out over the next 13 weeks. Track DSO and chase receivables before they age.'),
    ('Monthly Reporting', 'reporting', 'Reports delivered on schedule, with the numbers explained in plain words.'),
    ('CFO-Lite Support', 'cfo-lite', 'Guidance on hiring, pricing and growth decisions, without a full-time CFO.'),
    ('Finance Operations', 'finance-ops', 'Receivables and reporting run day to day, so the firm can get back to its clients.'),
]
PEOPLE = [
    ('joel', 'Joel Schenk', 'Founder & Chief Executive Officer', 'https://www.linkedin.com/in/joel-schenk/'),
    ('himanshu', 'Himanshu Sachdeva', 'Managing Director', 'https://www.linkedin.com/in/ca-himanshu-sachdeva/'),
    ('twisha', 'Twisha Gajjar', 'Finance Analyst', 'https://www.linkedin.com/in/twishagajjar/'),
]
# Company profiles (LinkedIn company page, Google Business Profile, Clutch ...). Add URLs here when available.
ORG_SAME_AS = []


def url_of(page):
    return SITE + '/' + ('' if page == 'index.html' else page[:-5])   # clean URLs: /services, /about-us ...


def md_of(page):
    return page[:-5] + '.md'


def org_node():
    people = [{'@type': 'Person', '@id': f'{SITE}/#{pid}', 'name': n, 'jobTitle': t, 'sameAs': [li],
               'worksFor': {'@id': f'{SITE}/#org'}} for pid, n, t, li in PEOPLE]
    node = {
        '@type': ['Organization', 'ProfessionalService'], '@id': f'{SITE}/#org',
        'name': 'Master Your Finance', 'alternateName': 'MYF', 'url': SITE + '/',
        'logo': SITE + '/assets/logo-green.svg', 'image': IMG,
        'description': PAGES['index.html'][1], 'email': EMAIL,
        'address': {'@type': 'PostalAddress', 'addressCountry': 'NL'},
        'areaServed': [{'@type': 'Country', 'name': c} for c in ('United States', 'United Kingdom', 'Australia')],
        'knowsAbout': ['Bookkeeping', 'Financial reporting', 'Cash flow forecasting', 'Law firm finance', 'Outsourced CFO services'],
        'contactPoint': [{'@type': 'ContactPoint', 'contactType': 'sales', 'email': EMAIL,
                          'url': SITE + '/contact-us', 'availableLanguage': ['English']}],
        'founder': {'@id': f'{SITE}/#joel'},
        'employee': people,
        'hasOfferCatalog': {'@type': 'OfferCatalog', 'name': 'Finance services', 'itemListElement': [
            {'@type': 'Offer', 'itemOffered': {'@id': f'{SITE}/services#{sid}'}} for _, sid, _ in SERVICES]},
        'potentialAction': {'@type': 'ScheduleAction', 'name': 'Book a free 30-minute finance review', 'target': CALENDLY},
    }
    if ORG_SAME_AS:
        node['sameAs'] = ORG_SAME_AS
    return node


def service_nodes():
    return [{'@type': 'Service', '@id': f'{SITE}/services#{sid}', 'name': n, 'description': d, 'url': f'{SITE}/services#{sid}',
             'serviceType': n, 'provider': {'@id': f'{SITE}/#org'},
             'areaServed': ['United States', 'United Kingdom', 'Australia'],
             'audience': {'@type': 'BusinessAudience', 'audienceType': 'Professional service firms'}} for n, sid, d in SERVICES]


def faq_node(page, faqs):
    return {'@type': 'FAQPage', '@id': url_of(page) + '#faq', 'mainEntity': [
        {'@type': 'Question', 'name': q, 'acceptedAnswer': {'@type': 'Answer', 'text': a}} for q, a in faqs]}


def graph(page, title, desc, faqs):
    url = url_of(page)
    nodes = [org_node(),
             {'@type': 'WebSite', '@id': f'{SITE}/#website', 'url': SITE + '/', 'name': 'Master Your Finance',
              'publisher': {'@id': f'{SITE}/#org'}, 'inLanguage': 'en'},
             {'@type': PAGE_TYPE.get(page, 'WebPage'), '@id': url + '#webpage', 'url': url, 'name': title, 'description': desc,
              'isPartOf': {'@id': f'{SITE}/#website'}, 'about': {'@id': f'{SITE}/#org'}, 'inLanguage': 'en',
              'dateModified': LASTMOD.get(page)}]
    if page != 'index.html':
        nodes.append({'@type': 'BreadcrumbList', '@id': url + '#breadcrumb', 'itemListElement': [
            {'@type': 'ListItem', 'position': 1, 'name': 'Home', 'item': SITE + '/'},
            {'@type': 'ListItem', 'position': 2, 'name': NAMES[page], 'item': url}]})
    if page in ('index.html', 'services.html'):
        nodes += service_nodes()
    if faqs:
        nodes.append(faq_node(page, faqs))
    if page == 'health-check.html':
        nodes.append({'@type': 'WebApplication', '@id': url + '#app', 'name': 'Law Firm Revenue Health Check',
                      'url': url, 'applicationCategory': 'BusinessApplication', 'operatingSystem': 'Any (web browser)',
                      'offers': {'@type': 'Offer', 'price': '0', 'priceCurrency': 'USD'}, 'provider': {'@id': f'{SITE}/#org'}})
    return {'@context': 'https://schema.org', '@graph': nodes}


def esc(s):
    return s.replace('&', '&amp;').replace('"', '&quot;').replace('<', '&lt;')


def seo_block(page, title, desc, faqs=None):
    url = url_of(page)
    out = [
        '<!--seo:start-->',
        f'<title>{esc(title)}</title>',
        f'<meta name="description" content="{esc(desc)}">',
        f'<link rel="canonical" href="{url}">',
        f'<link rel="alternate" type="text/markdown" href="/{md_of(page)}" title="Markdown version for AI agents">',
        '<link rel="describedby" type="text/plain" href="/llms.txt">',
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
        '<script type="application/ld+json">' + json.dumps(graph(page, title, desc, faqs), ensure_ascii=False).replace('</', '<\\/') + '</script>',
        '<script src="assets/webmcp.js" defer></script>',
        '<!--seo:end-->',
    ]
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
    html = re.sub(r'class="myf([^"]*)"', lambda m: 'class="myf' + m.group(1).replace('rv-ready', '') + '"', html, count=1)
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


# ---------- Markdown copies for agents ----------
READABLE_JS = """(root) => {
  const c = root.cloneNode(true);
  c.querySelectorAll('header, script, style, svg, button, video, img, input, select, textarea, form, [aria-hidden="true"], [hidden], .vd-hint, .yt-chip, .gps, .gps-stage').forEach(e => e.remove());
  c.querySelectorAll('.sr-only').forEach(e => { if (/new tab/i.test(e.textContent)) e.remove(); });
  c.querySelectorAll('span, a, b, strong').forEach(e => { if (e.nextSibling && e.nextSibling.nodeType === 1) e.after(' '); });
  c.querySelectorAll('a[href]').forEach(a => { try { a.setAttribute('href', new URL(a.getAttribute('href'), location.href).href.replace(location.origin, '%SITE%').replace(/\\.html(#|$)/, '$1').replace('%SITE%/index', '%SITE%/')); } catch (e) {} });
  return c.innerHTML;
}"""


def to_markdown(html, page, title, desc):
    md = markdownify(html, heading_style='ATX', bullets='-', strip=['span'])
    md = re.sub(r'[ \t]+\n', '\n', md)
    md = re.sub(r'\n{3,}', '\n\n', md).strip()
    head = (f'# {title}\n\n> {desc}\n\nSource: {url_of(page)}  \n'
            f'Contact: {EMAIL} · Book a free 30-minute finance review: {CALENDLY}\n\n---\n\n')
    return head + md + '\n'


def faqs_on_page(pg):
    return pg.evaluate("""() => [...document.querySelectorAll('#app .acc')].map(a => {
      const q = a.querySelector('.acc-btn'); const p = a.querySelector('.acc-in');
      return [q ? q.innerText.trim() : '', p ? p.innerText.trim() : ''];
    }).filter(x => x[0] && x[1])""")


def templates_for(page):
    s = open(os.path.join(ROOT, page), encoding='utf-8').read()
    names = re.findall(r"name:\s*['\"]([A-Za-z]+)['\"]", s)
    return [page] + [f'{n}.dc.html' for n in names if os.path.exists(os.path.join(ROOT, f'{n}.dc.html'))]


def lastmod(files):
    """Date the page content last changed: newest git commit of its template files, or today if they have uncommitted edits."""
    today = datetime.date.today().isoformat()
    try:
        dirty = subprocess.run(['git', 'status', '--porcelain', '--'] + files, cwd=ROOT, capture_output=True, text=True).stdout.strip()
        if dirty:
            return today
        d = subprocess.run(['git', 'log', '-1', '--format=%cs', '--'] + files, cwd=ROOT, capture_output=True, text=True).stdout.strip()
        return d or today
    except Exception:
        return today


LASTMOD = {}


def main():
    for page in list(PAGES) + ['health-check.html']:
        tpl = templates_for(page)
        LASTMOD[page] = lastmod([f for f in tpl if f.endswith('.dc.html')] or tpl)
    md_pages = {}
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
            faqs = faqs_on_page(pg)
            readable = pg.evaluate(READABLE_JS.replace('%SITE%', SITE), pg.query_selector('#app > .myf'))
            s = put_pre(put_seo(s, seo_block(page, title, desc, faqs)), html)
            open(path, 'w', encoding='utf-8').write(s)
            md_pages[page] = to_markdown(readable, page, title, desc)
            words = len(re.sub(r'<[^>]+>', ' ', html).split())
            print(f'{page}: {words} words of plain HTML, {len(faqs)} FAQs, lastmod {LASTMOD[page]}')
        # health check page (plain HTML page, no template)
        pg.goto(f'{LOCAL}/health-check.html'); pg.wait_for_timeout(1500)
        hc_readable = pg.evaluate(READABLE_JS.replace('%SITE%', SITE), pg.query_selector('body'))
        b.close()

    hc = os.path.join(ROOT, 'health-check.html')
    s = open(hc, encoding='utf-8').read()
    t = re.search(r'<title>([^<]*)</title>', s).group(1).replace('&amp;', '&')
    d = re.search(r'<meta name="description" content="([^"]*)"', s).group(1).replace('&amp;', '&')
    s = put_seo(s, seo_block('health-check.html', t, d))
    open(hc, 'w', encoding='utf-8').write(s)
    md_pages['health-check.html'] = to_markdown(hc_readable, 'health-check.html', t, d)

    for page, md in md_pages.items():
        open(os.path.join(ROOT, md_of(page)), 'w', encoding='utf-8').write(md)

    all_pages = list(PAGES) + ['health-check.html']
    open(os.path.join(ROOT, 'sitemap.xml'), 'w').write(
        '<?xml version="1.0" encoding="UTF-8"?>\n<urlset xmlns="http://www.sitemaps.org/schemas/sitemap/0.9">\n'
        + ''.join(f'  <url><loc>{url_of(p)}</loc><lastmod>{LASTMOD[p]}</lastmod></url>\n' for p in all_pages) + '</urlset>\n')

    open(os.path.join(ROOT, 'robots.txt'), 'w').write(
        '# Content Signals (https://contentsignals.org): search engines may index this site, AI assistants may use it\n'
        '# to answer questions and link to us, but the content may not be used to train AI models.\n'
        'User-agent: *\nContent-Signal: search=yes, ai-input=yes, ai-train=no\nAllow: /\nDisallow: /scripts/\nDisallow: /api/\n\n'
        f'Sitemap: {SITE}/sitemap.xml\n')

    def line(p, note):
        return f'- [{NAMES[p]}]({SITE}/{md_of(p)}): {note}'
    llms = [
        '# Master Your Finance', '',
        '> Master Your Finance (MYF) is an outsourced finance team for professional service firms (law firms, agencies, '
        'IT and consulting firms, startups) in the United States, the United Kingdom and Australia. We handle bookkeeping, '
        'monthly reporting, 13-week cash flow forecasting, CFO-lite support and finance operations.', '',
        f'Based in the Netherlands. Contact: {EMAIL}. Book a free 30-minute finance review: {CALENDLY}. '
        'Every page below is also available as HTML at the same address without ".md".', '',
        '## Main pages',
        line('index.html', 'what MYF does, how it works (the Financial GPS), who it is for, team and FAQs'),
        line('services.html', 'the five services, what is included in each, pricing approach and setup FAQs'),
        line('industries.html', 'how MYF works with law firms, agencies, IT and consulting firms, other professional services and startups'),
        line('about-us.html', 'who we are, mission and vision, how we work, the team'),
        line('contact-us.html', 'book a free 30-minute finance review or send an enquiry'), '',
        '## Free tools',
        line('tools.html', 'free self-assessment tools: Financial GPS snapshot, utilisation, realisation and DSO checks, cash runway estimator, 30-day sprint planner'),
        line('health-check.html', 'interactive revenue health check for law firms (runs in the browser)'), '',
        '## For agents',
        f'- [MCP server card]({SITE}/.well-known/mcp/server-card.json): read-only MCP server with tools to read these pages',
        f'- [Sitemap]({SITE}/sitemap.xml)', '',
        '## Optional',
        line('privacy-policy.html', 'how personal data from the website and forms is handled'),
        line('terms.html', 'terms for using the website and free tools; content is information only, not financial advice'), '',
    ]
    open(os.path.join(ROOT, 'llms.txt'), 'w', encoding='utf-8').write('\n'.join(llms))
    print('health-check.html, Markdown copies, llms.txt, sitemap.xml, robots.txt updated')


if __name__ == '__main__':
    main()
