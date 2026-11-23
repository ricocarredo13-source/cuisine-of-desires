/* Cuisine of Desires — accessible sticky scrollspy navigation */
(() => {
  'use strict';
  const $ = (selector) => document.querySelector(selector);
  const nav = $('#desktop-nav');
  const sectionsRoot = $('#sections');
  const select = $('#section-select');
  const drawer = $('#about-drawer');
  const overlay = $('#drawer-overlay');
  const openButton = $('#menu-open');
  const closeButton = $('#menu-close');
  const aboutButton = $('#footer-about');
  let targets = [];
  let frameQueued = false;
  let focusBeforeDrawer = null;

  function safeSectionId(id) { return /^[a-z0-9-]+$/.test(id) ? id : ''; }
  function addSection(section, index) {
    const id = safeSectionId(section.id);
    if (!id) return;
    const article = document.createElement('section');
    article.className = 'recipe-section';
    article.id = id;
    article.setAttribute('aria-labelledby', `heading-${id}`);
    const n = document.createElement('span');
    n.className = 'section-number';
    n.textContent = String(index + 1).padStart(2, '0') + ' / THE RECIPE';
    const heading = document.createElement('h2');
    heading.id = `heading-${id}`;
    heading.textContent = section.title;
    const body = document.createElement('div');
    body.className = 'section-body';
    // HTML here is built server-side from allowlisted Notion blocks, never visitor input.
    body.innerHTML = section.html;
    article.append(n, heading, body);
    sectionsRoot.append(article);
    const a = document.createElement('a');
    a.className = 'toc-link';
    a.href = `#${id}`;
    a.textContent = section.title;
    a.dataset.target = id;
    nav.append(a);
    const option = document.createElement('option');
    option.value = id;
    option.textContent = section.title;
    select.append(option);
    targets.push({ id, node: article, link: a });
  }

  function setActive(id) {
    for (const target of targets) {
      const active = target.id === id;
      target.link.classList.toggle('active', active);
      if (active) target.link.setAttribute('aria-current', 'location');
      else target.link.removeAttribute('aria-current');
    }
    if (select.value !== id) select.value = id;
  }
  function updateActive() {
    frameQueued = false;
    if (!targets.length) return;
    const line = Math.min(window.innerHeight * .32, 285);
    let active = targets[0].id;
    for (const item of targets) {
      if (item.node.getBoundingClientRect().top <= line) active = item.id;
    }
    if (window.innerHeight + window.scrollY >= document.documentElement.scrollHeight - 8) active = targets.at(-1).id;
    setActive(active);
  }
  function requestActive() {
    if (!frameQueued) { frameQueued = true; requestAnimationFrame(updateActive); }
  }
  function goTo(id) {
    const match = targets.find(s => s.id === id);
    if (!match) return;
    const reducedMotion = window.matchMedia('(prefers-reduced-motion: reduce)').matches;
    match.node.scrollIntoView({ behavior: reducedMotion ? 'auto' : 'smooth', block: 'start' });
    if (window.location.hash !== `#${id}`) history.replaceState(null, '', `#${id}`);
    setActive(id);
  }
  nav.addEventListener('click', e => {
    const a = e.target.closest('a[data-target]');
    if (a) { e.preventDefault(); goTo(a.dataset.target); }
  });
  select.addEventListener('change', () => goTo(select.value));
  window.addEventListener('scroll', requestActive, { passive: true });
  window.addEventListener('resize', requestActive);

  function openDrawer() {
    focusBeforeDrawer = document.activeElement;
    drawer.inert = false;
    drawer.setAttribute('aria-hidden', 'false');
    overlay.hidden = false;
    document.body.classList.add('drawer-open');
    openButton.setAttribute('aria-expanded', 'true');
    requestAnimationFrame(() => { overlay.classList.add('visible'); drawer.classList.add('open'); closeButton.focus(); });
  }
  function closeDrawer() {
    drawer.classList.remove('open');
    overlay.classList.remove('visible');
    drawer.setAttribute('aria-hidden', 'true');
    drawer.inert = true;
    document.body.classList.remove('drawer-open');
    openButton.setAttribute('aria-expanded', 'false');
    // Delay hiding backdrop until transition completes; reduced motion is harmless.
    setTimeout(() => { if (!drawer.classList.contains('open')) overlay.hidden = true; }, 330);
    focusBeforeDrawer?.focus();
  }
  openButton.addEventListener('click', openDrawer);
  closeButton.addEventListener('click', closeDrawer);
  aboutButton.addEventListener('click', openDrawer);
  overlay.addEventListener('click', closeDrawer);
  document.addEventListener('keydown', e => {
    if (e.key === 'Escape' && drawer.classList.contains('open')) closeDrawer();
    if (e.key === 'Tab' && drawer.classList.contains('open')) {
      const nodes = [...drawer.querySelectorAll('a[href],button:not([disabled]),[tabindex]:not([tabindex="-1"])')];
      if (!nodes.length) return;
      const first = nodes[0], last = nodes[nodes.length - 1];
      if (e.shiftKey && document.activeElement === first) { e.preventDefault(); last.focus(); }
      else if (!e.shiftKey && document.activeElement === last) { e.preventDefault(); first.focus(); }
    }
  });

  async function init() {
    try {
      let content = window.__CUISINE_PREVIEW__;
      if (!content) {
        const response = await fetch('./content.json', { cache: 'no-cache' });
        if (!response.ok) throw new Error(`HTTP ${response.status}`);
        content = await response.json();
      }
      document.title = `${content.brand} — ${content.title}`;
      $('#brand-name').textContent = content.brand;
      if (content.heroUrl && /^\.\/assets\/notion-media\/[a-zA-Z0-9_.-]+$/.test(content.heroUrl)) {
        $('.hero').style.backgroundImage = `linear-gradient(90deg,rgba(8,7,8,.18),rgba(8,7,8,.04) 43%,rgba(8,7,8,.3)),url('${content.heroUrl}')`;
      }
      $('#footer-brand').textContent = content.brand;
      $('#recipe-title').textContent = content.title;
      $('#recipe-byline').textContent = content.byline;
      // The short italic paragraph above the recipe's H1 in Notion is
      // exported as `tagline`. Show it below the byline when provided.
      const tagline = $('#recipe-tagline');
      const taglineText = typeof content.tagline === 'string' ? content.tagline.trim() : '';
      tagline.textContent = taglineText;
      tagline.hidden = !taglineText;
      $('#about-content').innerHTML = content.aboutHtml || '<p>About the creators will be added here.</p>';
      sectionsRoot.textContent = '';
      content.sections.forEach(addSection);
      if (!targets.length) throw new Error('No sections returned. Check the headings in Notion.');
      const hashId = decodeURIComponent(window.location.hash.replace(/^#/, ''));
      if (targets.some(t => t.id === hashId)) setTimeout(() => goTo(hashId), 80);
      else updateActive();
    } catch (error) {
      sectionsRoot.textContent = '';
      const p = document.createElement('p');
      p.className = 'loading-note';
      p.textContent = 'The recipe could not load. Open this site through a web server, or check content.json.';
      sectionsRoot.append(p);
      console.error('Cuisine of Desires:', error);
    }
  }
  init();
})();
