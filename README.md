# Cuisine of Desires — ENG 11 website

A no-framework website based on Group 4's original visual mockup: black masthead, cookie photography, gothic typography, burgundy accent, a **permanently visible sticky table of contents**, **scrollspy** (active section automatically turns red), a working About-the-Creators drawer, and a mobile-friendly jump menu.

**Notion is the editor. GitHub Pages is the public website.** Visitors **do not** need a Notion or GitHub account. Notion itself can stay private; only intentionally exported content is public.

## What's already ready

- `site/index.html`, `site/styles.css`, `site/script.js`: working static frontend.
- `site/content.json`: starter copy taken from our existing Notion draft. Placeholders are **not** approved final group content.
- `site/assets/cookie-hero.jpg`: a *temporary crop from the group's supplied mockup*. Before publishing publicly, confirm permission to reuse the underlying photo or replace it with an original/licensed image. The default page cover in Notion can override this photo when synchronized.
- `scripts/sync_notion.py`: secure Notion API exporter. Python standard library only; no packages needed.
- `.github/workflows/deploy.yml`: auto-sync + GitHub Pages deployment (every 30 minutes, on push, or manually).
- `tests/test_sync.py`: quick parser/security tests.

## First: see the prototype locally

**Fastest:** Double-click `preview-standalone.html`. It is fully self-contained and opens directly in a browser, with functioning section navigation and the About menu. It is a frozen preview, **not** the live Notion-synced website.

To test the actual multi-file website locally:

1. Unzip this folder.
2. Open a terminal in this folder.
3. Run `python -m http.server 8000 --directory site` (on Windows, `py -m http.server 8000 --directory site` also works).
4. Open `http://localhost:8000`.

> Do not double-click `site/index.html`: browsers often block the local `fetch('./content.json')`. A local web server is required.

## Connect the existing Notion page

Our current content pages are:

- Main: `https://app.notion.com/p/420486ee78e881e1bcb2d8bb046ee0b2`
- About: `https://app.notion.com/p/420486ee78e881a5a994d1739df0bcfa`

These page IDs are already the *default* values inside the exporter, so you won't need to paste them unless you move to another page.

### 1. Create a read-only Notion connection

In Notion, the **workspace owner** should go to `Settings → Connections` / Notion's Developer Portal and create an **internal connection** named e.g. `Cuisine of Desires Website`. Grant **Read content** access, not editing rights. Copy the connection's secret token. **Never paste the secret into chat, HTML, JavaScript, or a public repository.**

Open the main Notion page → `••• → Connections` or `Add connections` → add the new integration. Ensure the About child page is accessible as well (share it separately if the API returns a 404 for that page).

**Important guest-workspace caveat:** If you see “You're a guest in [someone else's] Notion,” the owner/admin of that workspace may need to create or authorize the internal connection. An integration created in your *own* unrelated workspace will not automatically read someone else's guest page. Alternatively, duplicate the content into your own workspace and update the two IDs using GitHub repository variables.

### 2. Publish the repository using GitHub Desktop (no terminal needed)

1. Create or sign into a GitHub account, and install **GitHub Desktop** if needed.
2. Unzip this project, and create a Git repository in that extracted folder using GitHub Desktop (`File → Add local repository`; if asked, choose `Create a repository here`).
3. Commit all source files, then choose `Publish repository`. On a GitHub Free plan, make the repository **Public** to use GitHub Pages for free.
4. On GitHub, open your repository → `Settings → Pages` → `Build and deployment → Source: GitHub Actions`.
5. Open `Settings → Secrets and variables → Actions → Secrets → New repository secret`:
   - **Name:** `NOTION_TOKEN`
   - **Value:** the secret copied from Notion.
6. Only if using different Notion pages, open the **Variables** tab on that same settings screen and create:
   - `NOTION_PAGE_ID` = the main page ID.
   - `NOTION_ABOUT_PAGE_ID` = the About page ID.
7. Go to your GitHub repository `Actions` tab. Choose **Publish Notion content to Cuisine of Desires** → **Run workflow** on branch `main`.
8. After it finishes successfully, find your public URL in `Settings → Pages`. The form is usually `https://YOUR-USERNAME.github.io/YOUR-REPOSITORY/`.

### 3. Edit the website in Notion afterward

| Edit this in Notion | What updates on the public site |
| --- | --- |
| Main page title (`Cuisine of Desires`) | Black header brand |
| First `Heading 1` (`Chocolate Chip Cookie...`) | Large recipe title |
| `By Group 4 · November 23, 2026` paragraph | Byline |
| Each `Heading 2` (`Introduction`, `Ingredients`, etc.) | An **automatic navigation section**, in Notion order |
| Text / formatted text / bulleted or numbered items under each H2 | Section content |
| Images under the sections | Images on the public site (downloaded during build) |
| YouTube video embedded under **Video Tutorial** | Responsive video player |
| Main page **cover image** | Cookie hero photo (overrides included placeholder) |
| Separate About child page | Hamburger menu's contents |

Save in Notion. GitHub Actions checks for changes on a best-effort **30-minute schedule**. To update immediately, choose **Actions → Publish Notion content… → Run workflow**. GitHub scheduled runs may be delayed; they are not real-time.

### Key content formatting rules

- Use **Heading 1** once for the recipe title.
- Use **Heading 2** for each major recipe section. The table of contents is created automatically from all H2 blocks, so you can add a “Recipe Card” section too.
- Use **Heading 3** for subsections *inside* a recipe section.
- Put the content between H2 headings. This exporter does not treat regular Notion columns as public website columns; the website controls layout.
- To show a working video player, embed a **YouTube** or **Vimeo** video. Unsupported embeds render as links.
- This starter supports text, links, basic formatting, quotes, lists, images, and YouTube/Vimeo videos. More complex databases, interactive Notion widgets, tables, uploaded large videos, and custom Notion block styling are not included.
- Don't include private discussions or group contact information in these pages. **Everything exported is public.**

## Test synchronization locally (optional)

Mac/Linux:

```bash
export NOTION_TOKEN='secret_from_your_notion_connection'
python scripts/sync_notion.py
python -m http.server 8000 --directory site
```

Windows PowerShell:

```powershell
$env:NOTION_TOKEN = 'secret_from_your_notion_connection'
py scripts/sync_notion.py
py -m http.server 8000 --directory site
```

To check the parser tests:

```bash
python -m unittest discover -s tests -v
```

Never store the token in `.env`, a commit, or a screenshot. The app runs on the static content JSON at viewing time; **the token is only used privately in GitHub Actions to create the JSON**, never in visitors' browsers.

## Custom design changes

- Colors and font scale: `site/styles.css`, top `:root` variables.
- Header, divider, sidebar and About drawer markup: `site/index.html`.
- Section highlighting, smooth scroll, menu state and mobile navigation: `site/script.js`.
- Temporary photograph: `site/assets/cookie-hero.jpg` (but a Notion main-page cover takes priority after sync).

This intentionally separates **Notion-managed words, headings, and media** from **code-managed layout, animation, and interaction**. Editing a Notion page won't rewrite CSS or JavaScript.

## Troubleshooting

- **`NOTION_TOKEN is not set`** in Actions: add the secret under the repository's Actions secrets.
- **Notion 404**: the internal connection cannot see the page; add it to both Notion pages, or use correct IDs.
- **Notion 403**: insufficient workspace permissions or missing Read content capability.
- **Notion says guest access**: ask the workspace owner to authorize the connection or duplicate pages into your own workspace.
- **Blank navigator**: use actual Heading 2 blocks, not bold paragraphs.
- **`No H2 headings found`**: create sections formatted as Heading 2 in Notion.
- **No video embed**: use a YouTube/Vimeo video block or external embedded URL; large files may not export.
- **Changes not immediately visible**: run the GitHub Action manually or wait for the scheduled run; hard-refresh the website.
- **No deployed site URL**: verify Settings → Pages → Build and deployment uses GitHub Actions.
- **GitHub Free public repository**: project files and published content are public. Keep only the Notion API token private via a secret.

## Official references

- Notion internal connections: https://www.notion.com/help/create-integrations-with-the-notion-api
- Notion block API: https://developers.notion.com/reference/get-block-children
- GitHub Pages Actions: https://docs.github.com/en/pages/getting-started-with-github-pages/using-custom-workflows-with-github-pages
- GitHub Actions secrets: https://docs.github.com/en/actions/how-tos/write-workflows/choose-what-workflows-do/use-secrets
