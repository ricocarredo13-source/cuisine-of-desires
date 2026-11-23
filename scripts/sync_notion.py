#!/usr/bin/env python3
"""Fetch selected Notion pages and publish a safe static JSON document.

No token is ever delivered to the browser. Set NOTION_TOKEN as a GitHub Actions
secret. Text is HTML-escaped; supported formatting is rendered as allowlisted
HTML. Embedded YouTube videos are converted to privacy-enhanced iframes.
"""
from __future__ import annotations

import html
import json
import mimetypes
import os
import re
import sys
import time
from pathlib import Path
from urllib.parse import quote, urlencode, urlparse, parse_qs
from urllib.request import Request, urlopen
from urllib.error import HTTPError, URLError

ROOT = Path(__file__).resolve().parents[1]
SITE = ROOT / 'site'
MEDIA = SITE / 'assets' / 'notion-media'
PAGE_ID = os.getenv('NOTION_PAGE_ID') or '420486ee78e881e1bcb2d8bb046ee0b2'
ABOUT_ID = os.getenv('NOTION_ABOUT_PAGE_ID') or '420486ee78e881a5a994d1739df0bcfa'
TOKEN = os.getenv('NOTION_TOKEN', '')
VERSION = '2026-03-11'
HEADINGS = {'heading_1', 'heading_2', 'heading_3', 'heading_4'}
MAX_DOWNLOAD = 30 * 1024 * 1024


def notion_request(path: str, params: dict | None = None) -> dict:
    url = 'https://api.notion.com/v1/' + path.lstrip('/')
    if params:
        url += '?' + urlencode(params)
    req = Request(url, headers={
        'Authorization': 'Bearer ' + TOKEN,
        'Notion-Version': VERSION,
        'Accept': 'application/json',
        'User-Agent': 'CuisineOfDesiresSync/1.0'
    })
    for attempt in range(4):
        try:
            with urlopen(req, timeout=35) as res:
                return json.loads(res.read().decode('utf-8'))
        except HTTPError as exc:
            detail = exc.read(400).decode('utf-8', errors='replace')
            if exc.code == 429 and attempt < 3:
                time.sleep(min(8, int(exc.headers.get('Retry-After', '2'))))
                continue
            raise RuntimeError(f'Notion API {exc.code}: {detail}') from exc
    raise RuntimeError('Notion API rate-limit retries exceeded')


def children(block_id: str) -> list[dict]:
    all_blocks = []
    cursor = None
    while True:
        params = {'page_size': 100}
        if cursor:
            params['start_cursor'] = cursor
        data = notion_request(f'blocks/{quote(block_id)}/children', params)
        all_blocks.extend(data.get('results', []))
        if not data.get('has_more'):
            return all_blocks
        cursor = data.get('next_cursor')
        if not cursor:
            raise RuntimeError('Notion pagination said has_more without a cursor')


def rich_plain(items: list[dict]) -> str:
    return ''.join(item.get('plain_text') or item.get('text', {}).get('content', '') for item in (items or []))


def clean_url(url: str) -> str:
    try:
        parsed = urlparse(url)
        if parsed.scheme in {'https', 'http', 'mailto'} and parsed.netloc if parsed.scheme != 'mailto' else bool(parsed.path):
            return url
    except (ValueError, TypeError):
        pass
    return ''


def rich_html(items: list[dict]) -> str:
    result = []
    for item in items or []:
        value = html.escape(item.get('plain_text') or item.get('text', {}).get('content', ''))
        value = value.replace('\n', '<br>')
        styles = item.get('annotations', {})
        if styles.get('code'): value = f'<code>{value}</code>'
        if styles.get('bold'): value = f'<strong>{value}</strong>'
        if styles.get('italic'): value = f'<em>{value}</em>'
        if styles.get('strikethrough'): value = f'<s>{value}</s>'
        if styles.get('underline'): value = f'<u>{value}</u>'
        link = clean_url(item.get('href') or (item.get('text') or {}).get('link', {}).get('url', '') if isinstance((item.get('text') or {}).get('link'), dict) else item.get('href', ''))
        if link:
            value = f'<a href="{html.escape(link, quote=True)}" target="_blank" rel="noopener noreferrer">{value}</a>'
        result.append(value)
    return ''.join(result)


def image_from_notion(obj: dict, filename_stem: str) -> str:
    source = obj.get(obj.get('type', ''), {}).get('url', '')
    if not source and 'file' in obj: source = obj['file'].get('url', '')
    if not source and 'external' in obj: source = obj['external'].get('url', '')
    if not source:
        return ''
    parsed = urlparse(source)
    if parsed.scheme != 'https' or not parsed.netloc:
        return ''
    MEDIA.mkdir(exist_ok=True, parents=True)
    req = Request(source, headers={'User-Agent': 'CuisineOfDesiresSync/1.0'})
    try:
        with urlopen(req, timeout=50) as res:
            mime = (res.headers.get('Content-Type', '').split(';')[0]).strip().lower()
            extensions = {'image/jpeg':'.jpg','image/png':'.png','image/webp':'.webp','image/gif':'.gif'}
            if mime not in extensions:
                print('Skipping unsupported image format:', mime, file=sys.stderr)
                return ''
            if int(res.headers.get('Content-Length', '0')) > MAX_DOWNLOAD:
                print('Skipping image over size limit', file=sys.stderr)
                return ''
            data = res.read(MAX_DOWNLOAD + 1)
            if len(data) > MAX_DOWNLOAD:
                print('Skipping oversized image', file=sys.stderr)
                return ''
            dest = MEDIA / (filename_stem + extensions[mime])
            dest.write_bytes(data)
            return './assets/notion-media/' + dest.name
    except (HTTPError, URLError, TimeoutError, OSError) as exc:
        print(f'Image download failed ({filename_stem}): {exc}', file=sys.stderr)
        return ''


def video_html(url: str) -> str:
    safe = clean_url(url)
    if not safe: return ''
    parsed = urlparse(safe)
    host = (parsed.hostname or '').lower()
    vid = ''
    if host in {'youtube.com','www.youtube.com','m.youtube.com','youtube-nocookie.com','www.youtube-nocookie.com'}:
        if parsed.path == '/watch': vid = parse_qs(parsed.query).get('v', [''])[0]
        elif parsed.path.startswith(('/embed/', '/shorts/')): vid = parsed.path.strip('/').split('/')[-1]
    elif host in {'youtu.be','www.youtu.be'}:
        vid = parsed.path.strip('/').split('/')[0]
    if re.fullmatch(r'[a-zA-Z0-9_-]{11}', vid):
        return f'<iframe title="Group cooking video tutorial" loading="lazy" allow="accelerometer; autoplay; clipboard-write; encrypted-media; gyroscope; picture-in-picture" allowfullscreen src="https://www.youtube-nocookie.com/embed/{vid}"></iframe>'
    if host in {'vimeo.com','www.vimeo.com'}:
        match = re.fullmatch(r'/([0-9]+)', parsed.path)
        if match:
            return f'<iframe title="Group cooking video tutorial" loading="lazy" allow="fullscreen; picture-in-picture" allowfullscreen src="https://player.vimeo.com/video/{match.group(1)}"></iframe>'
    return f'<p><a href="{html.escape(safe,quote=True)}" target="_blank" rel="noopener noreferrer">Watch the video tutorial ↗</a></p>'


def child_render(block: dict, depth: int = 0) -> str:
    if depth > 7:
        return ''
    t = block.get('type', '')
    data = block.get(t, {}) or {}
    rtext = rich_html(data.get('rich_text', []))

    # A Notion column_list contains separate column blocks. Their children
    # must remain in distinct wrappers rather than being flattened vertically.
    if t == 'column_list':
        columns = children(block['id']) if block.get('has_children') else []
        rendered_columns = []
        for column in columns:
            if column.get('type') != 'column':
                continue
            column_blocks = children(column['id']) if column.get('has_children') else []
            column_html = render_blocks(column_blocks, depth + 2)
            rendered_columns.append(f'<div class="notion-column">{column_html}</div>')
        if not rendered_columns:
            return ''
        count = len(rendered_columns)
        return (f'<div class="notion-columns" style="--notion-column-count:{count}">'
                + ''.join(rendered_columns) + '</div>')

    nested = ''
    if block.get('has_children') and t not in {'child_page','child_database','table'}:
        nested = render_blocks(children(block['id']), depth + 1)
    if t == 'paragraph':
        stripped = rich_plain(data.get('rich_text', []))
        class_attr = ' class="placeholder"' if stripped.lstrip().startswith('[') and stripped.rstrip().endswith(']') else ''
        return f'<p{class_attr}>{rtext}</p>' if rtext else ''
    if t in HEADINGS:
        level = 'h3' if t in {'heading_1','heading_2','heading_3'} else 'h4'
        return f'<{level}>{rtext}</{level}>'
    if t == 'quote': return f'<blockquote>{rtext}{nested}</blockquote>'
    if t == 'callout': return f'<blockquote>{rtext}{nested}</blockquote>'
    if t == 'bulleted_list_item': return f'<li>{rtext}{nested}</li>'
    if t == 'numbered_list_item': return f'<li>{rtext}{nested}</li>'
    if t == 'to_do': return f'<p>{"☑" if data.get("checked") else "☐"} {rtext}</p>'
    if t == 'divider': return '<hr>'
    if t == 'image':
        img = image_from_notion(data, str(block.get('id','img')).replace('-',''))
        caption = rich_html(data.get('caption', []))
        return f'<figure><img src="{html.escape(img,quote=True)}" alt="{html.escape(rich_plain(data.get("caption",[])) or "Recipe illustration",quote=True)}" loading="lazy">' + (f'<figcaption>{caption}</figcaption>' if caption else '') + '</figure>' if img else ''
    if t in {'video','embed','bookmark'}:
        source = data.get('external', {}).get('url') or data.get('url', '')
        if t == 'video' and not source:
            return '<p class="placeholder">[Upload your video to YouTube, then embed it in Notion to show it here.]</p>'
        return video_html(source)
    if t == 'code': return f'<pre><code>{html.escape(rich_plain(data.get("rich_text", [])))}</code></pre>'
    if t == 'toggle': return f'<details><summary>{rtext}</summary>{nested}</details>'
    return nested


def render_blocks(blocks: list[dict], depth: int = 0) -> str:
    chunks = []
    list_group = None
    for block in blocks:
        t = block.get('type')
        if t in {'bulleted_list_item','numbered_list_item'}:
            group = 'ul' if t == 'bulleted_list_item' else 'ol'
            if list_group != group:
                if list_group: chunks.append(f'</{list_group}>')
                chunks.append(f'<{group}>')
                list_group = group
            chunks.append(child_render(block, depth))
            continue
        if list_group: chunks.append(f'</{list_group}>'); list_group = None
        chunks.append(child_render(block, depth))
    if list_group: chunks.append(f'</{list_group}>')
    return '\n'.join(chunks)


def get_page_title(page: dict) -> str:
    properties = page.get('properties', {})
    for entry in properties.values():
        if entry.get('type') == 'title':
            return rich_plain(entry.get('title', []))
    return 'Cuisine of Desires'


def slugify(title: str) -> str:
    slug = re.sub(r'[^a-z0-9]+', '-', title.lower()).strip('-')
    return slug or 'section'


def compile_content(page: dict, blocks: list[dict], about_blocks: list[dict]) -> dict:
    brand = get_page_title(page)
    recipe_title = 'Chocolate Chip Cookie to Satisfy Your Hunger'
    byline = 'By Group 4 · November 23, 2026'
    tagline = ''
    sections = []
    in_section = False
    current = None
    for block in blocks:
        t = block.get('type', '')
        data = block.get(t, {}) or {}
        text = rich_plain(data.get('rich_text', []))
        if t == 'heading_1' and not in_section:
            recipe_title = text or recipe_title
            continue
        if t == 'heading_2':
            in_section = True
            current = {'id': slugify(text), 'title': text, 'blocks': []}
            sections.append(current)
            continue
        if not in_section:
            if t == 'paragraph':
                if re.match(r'^By\s+Group\s+\d+', text, flags=re.I):
                    byline = text
                elif not tagline and text:
                    tagline = text
            continue
        if current is not None:
            current['blocks'].append(block)
    # Protect against duplicate heading slugs (e.g., repeated "Recipe Card").
    seen = set()
    for section in sections:
        original = section['id']
        idx = 2
        while section['id'] in seen:
            section['id'] = f'{original}-{idx}'
            idx += 1
        seen.add(section['id'])
        section['html'] = render_blocks(section.pop('blocks'))
    if not sections:
        raise RuntimeError('No H2 headings found. Add Introduction, Ingredients, etc. as Heading 2 blocks in Notion.')
    return {'brand':brand, 'title':recipe_title, 'byline':byline, 'tagline':tagline,
            'sections':sections, 'aboutHtml':render_blocks(about_blocks),
            'source':'Notion API: approved page blocks'}


def main():
    if not TOKEN:
        sys.exit('NOTION_TOKEN is not set. Set a GitHub Actions secret or export it locally. No public content has been changed.')
    main_page = notion_request(f'pages/{quote(PAGE_ID)}')
    blocks = children(PAGE_ID)
    about_blocks = children(ABOUT_ID)
    content = compile_content(main_page, blocks, about_blocks)
    cover = main_page.get('cover')
    if cover and isinstance(cover, dict):
        hero = image_from_notion(cover, 'notion-cover')
        if hero: content['heroUrl'] = hero
    out = SITE / 'content.json'
    out.write_text(json.dumps(content, indent=2, ensure_ascii=False), encoding='utf-8')
    print(f'Synced {len(content["sections"])} sections, plus About content, from Notion to {out}')


if __name__ == '__main__':
    main()
