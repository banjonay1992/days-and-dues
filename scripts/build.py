#!/usr/bin/env python3
"""Render the static website; a single base URL keeps future domain changes consistent."""
from pathlib import Path
from html import escape
import json
import re

ROOT = Path(__file__).resolve().parents[1]

def render_all():
    config = json.loads((ROOT / 'site.json').read_text())
    base = config['url'].rstrip('/') + '/'
    pages = config['pages']
    def url(file): return base + ('' if file == 'index.html' else file)
    def a(file, label, current=''):
        active = ' aria-current="page"' if file == current else ''
        return f'<a href="{file}"{active}>{label}</a>'
    mainnav = [('features.html','The app'),('for-your-work.html','For your work'),('pricing.html','Pricing'),('support.html','Support')]
    for page in pages + [{'file':'404.html','title':'Page not found — Days & Dues','description':'Find your way back to Days & Dues.','label':'Page not found'}]:
        file=page['file']; canonical=url(file); title=escape(page['title']); desc=escape(page['description'],quote=True)
        graph=[{'@type':'Organization','@id':base+'#organization','name':config['name'],'url':base,'logo':base+'assets/days-and-dues-logo.png','email':config['email']},
               {'@type':'WebSite','@id':base+'#website','name':config['name'],'url':base,'publisher':{'@id':base+'#organization'}},
               {'@type':'WebPage','@id':canonical+'#page','name':page['title'],'description':page['description'],'url':canonical,'isPartOf':{'@id':base+'#website'},'inLanguage':'en-GB'}]
        if file=='index.html':
            graph.append({'@type':'SoftwareApplication','@id':base+'#app','name':config['name'],'url':base,'downloadUrl':config['app_store_url'],'operatingSystem':'iOS 17.0 or later','applicationCategory':'BusinessApplication','description':page['description'],'publisher':{'@id':base+'#organization'}})
        elif file!='404.html':
            graph.append({'@type':'BreadcrumbList','itemListElement':[{'@type':'ListItem','position':1,'name':'Home','item':base},{'@type':'ListItem','position':2,'name':page['label'],'item':canonical}]})
        schema=json.dumps({'@context':'https://schema.org','@graph':graph},ensure_ascii=False).replace('</','<\\/')
        nav=''.join(a(f,l,file) for f,l in mainnav)
        update='<div class="release-note"><span class="release-dot" aria-hidden="true"></span><p>The new iPhone update is with Apple for review. <a href="faq.html#the-update">What this means for you <span aria-hidden="true">↗</span></a></p></div>' if config['release_state']=='in_review' else ''
        body=(ROOT/'content'/file).read_text()
        doc=f'''<!doctype html>
<html lang="en-GB"><head>
<meta charset="utf-8"><meta name="viewport" content="width=device-width, initial-scale=1">
<title>{title}</title><meta name="description" content="{desc}">
<meta name="theme-color" content="#173e36"><meta name="robots" content="{'noindex, follow' if file=='404.html' else 'index, follow, max-image-preview:large'}">
<link rel="canonical" href="{canonical}"><link rel="sitemap" type="application/xml" href="sitemap.xml">
<meta property="og:type" content="website"><meta property="og:site_name" content="Days &amp; Dues"><meta property="og:locale" content="en_GB">
<meta property="og:title" content="{title}"><meta property="og:description" content="{desc}"><meta property="og:url" content="{canonical}">
<meta property="og:image" content="{base}assets/days-and-dues-logo.png"><meta property="og:image:width" content="1024"><meta property="og:image:height" content="1024"><meta property="og:image:alt" content="Days &amp; Dues monogram in ivory, pine and terracotta">
<meta name="twitter:card" content="summary"><meta name="twitter:title" content="{title}"><meta name="twitter:description" content="{desc}"><meta name="twitter:image" content="{base}assets/days-and-dues-logo.png"><meta name="twitter:image:alt" content="Days &amp; Dues logo">
<link rel="icon" type="image/png" href="assets/days-and-dues-logo.png"><link rel="apple-touch-icon" href="assets/apple-touch-icon.png"><link rel="manifest" href="site.webmanifest">
<link rel="stylesheet" href="styles.css"><script src="site.js" defer></script><script type="application/ld+json">{schema}</script>
</head><body class="page-{file.removesuffix('.html')}">
<a class="skip-link" href="#main">Skip to content</a>
<header class="site-header"><a class="wordmark" href="index.html" aria-label="Days and Dues home"><img src="assets/days-and-dues-logo.png" width="42" height="42" alt=""><span>Days <i>&amp;</i> Dues</span></a><nav class="desktop-nav" aria-label="Main">{nav}</nav><a class="header-cta" href="{config['app_store_url']}">View iPhone app <span aria-hidden="true">↗</span></a><details class="mobile-menu"><summary>Menu <span aria-hidden="true">＋</span></summary><nav aria-label="Mobile">{nav}{a('how-it-works.html','How it works',file)}{a('faq.html','Questions',file)}<a href="{config['app_store_url']}">View iPhone app ↗</a></nav></details></header>
{update}
<main id="main">{body}</main>
<footer class="site-footer"><div class="footer-top"><div><a class="wordmark" href="index.html"><img src="assets/days-and-dues-logo.png" width="42" height="42" alt=""><span>Days <i>&amp;</i> Dues</span></a><p>Your days. Your dues.<br>A little less admin.</p></div><nav aria-label="Explore"><span class="eyebrow">Explore</span>{a('features.html','The app')}{a('for-your-work.html','For your work')}{a('how-it-works.html','How it works')}{a('pricing.html','Pricing')}</nav><nav aria-label="Help and information"><span class="eyebrow">Good to know</span>{a('faq.html','Questions')}{a('support.html','Support')}{a('privacy.html','Privacy')}{a('terms.html','Terms')}</nav><div class="footer-note"><span class="eyebrow">Made for independent work</span><p>An iPhone home for clients, work, time and money.</p><a class="text-link" href="{config['app_store_url']}">View on the App Store ↗</a></div></div><div class="footer-bottom"><span>© 2026 Nathan Cole · Days &amp; Dues</span><span>Invoices in GBP. Tax estimates use UK sole-trader rules.</span><a href="sitemap.xml">Sitemap</a></div></footer>
</body></html>'''
        # The error page must resolve assets and navigation from nested missing URLs.
        # Use absolute paths instead of <base>, so the skip link stays on the missing URL.
        if file=='404.html':
            doc=re.sub(r'(href|src)="(?![a-z]+:|#|//)([^"]+)"', lambda match: f'{match[1]}="{base}{match[2]}"', doc)
        (ROOT/file).write_text(doc)
    sitemap='<?xml version="1.0" encoding="UTF-8"?>\n<urlset xmlns="http://www.sitemaps.org/schemas/sitemap/0.9">\n'+''.join(f'  <url><loc>{escape(url(p["file"]))}</loc><lastmod>{config["updated"]}</lastmod></url>\n' for p in pages)+'</urlset>\n'
    (ROOT/'sitemap.xml').write_text(sitemap)
    (ROOT/'robots.txt').write_text('User-agent: *\nAllow: /\n\nSitemap: '+base+'sitemap.xml\n')
    (ROOT/'site.webmanifest').write_text(json.dumps({'name':config['name'],'short_name':config['name'],'id':'./','start_url':'./','scope':'./','display':'browser','background_color':'#f7f4ec','theme_color':'#173e36','icons':[{'src':'assets/days-and-dues-logo.png','sizes':'1024x1024','type':'image/png'},{'src':'assets/apple-touch-icon.png','sizes':'180x180','type':'image/png'}]},indent=2)+'\n')
    (ROOT/'.nojekyll').touch()
    print('Built',len(pages),'pages, 404, sitemap, crawler file and web manifest.')

if __name__ == '__main__': render_all()
