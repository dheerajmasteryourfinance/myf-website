# Master Your Finance – website preview

A working preview of the new MYF homepage design, for review before the WordPress build.

## What's inside

| File | What it is |
|---|---|
| `index.html` | Homepage (desktop layout on computers and tablets, phone layout under 700px wide) |
| `tools.html` | All tools page |
| `health-check.html` | Restyled law firm revenue health check |
| `Main.dc.html`, `Mobile.dc.html`, `ToolsPage.dc.html`, `GPS.dc.html` | Page templates (edit text here) |
| `myf.css` | All styles and brand colours |
| `dc-runtime.js` | Small script that renders the templates and runs the animations |
| `assets/` | Logo, team photos, video thumbnail and software logos |

## Put it on GitHub Pages (about 5 minutes)

1. Sign in at github.com and click **New repository**.
2. Name it, for example `myf-website`, choose **Public**, and click **Create repository**.
   (GitHub Pages is free for public repositories. A private repo needs a paid plan.)
3. On the new repo page, click **uploading an existing file**.
4. Open the `myf-website` folder on your computer, select **everything inside it** (including the `assets` folder) and drag it into the browser. Click **Commit changes**.
5. Go to **Settings → Pages**. Under **Build and deployment**, set Source to **Deploy from a branch**, Branch to **main** and folder to **/ (root)**. Click **Save**.
6. Wait 1–2 minutes and refresh. GitHub shows your link, for example
   `https://YOUR-USERNAME.github.io/myf-website/`

Share that link for feedback. To update the site later, upload the changed files to the repo again; the link stays the same.

## Good to know

- Open the site through the GitHub link, not by double-clicking `index.html`. The templates load over the web, so a local double-click shows "Loading…".
- The "Why MYF?" video streams from masteryourfinance.org.
- The Book buttons go to the Calendly discovery-call link.
- The contact form is a mockup and does not send anything yet. It will be connected during the WordPress build.
- The Health check still contains an Airtable token in its code. Replace it before sharing the link widely.
- This preview is for review only. The final site will be rebuilt in WordPress with Elementor Pro.
