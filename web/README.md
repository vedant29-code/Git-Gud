# Git-Gud AI — Showcase & Landing Website ⚖️🔥

This is the static showcase and documentation website for **Git-Gud AI (The Pre-Commit Judge & Jury)**.

---

## ⚡ Quick Start (Run Locally)

The site has **zero build dependencies**, zero npm packages, and zero external API calls.

### Option 1: Direct File Open
Double-click `index.html` in your file explorer, or open it directly in any modern browser:
```bash
# Windows
start index.html

# macOS
open index.html

# Linux
xdg-open index.html
```

### Option 2: Local Python Server (Recommended)
From within this `web/` directory:
```bash
python -m http.server 8000
```
Then visit: [http://localhost:8000](http://localhost:8000)

---

## 📂 Project Structure

```
web/
├── index.html          # Semantic HTML5 single-page structure (11 core sections)
├── css/
│   └── styles.css      # Dark terminal theme, cyber accents, responsive layout
├── js/
│   ├── app.js          # Interactive controller: terminal typing, copy buttons, tabs, FAQ
│   └── scenarios.js    # Data store for the 4 demo commits, diffs, and roasts
├── assets/
│   ├── favicon.svg     # Scalable vector gavel + terminal icon
│   ├── mascot.svg      # Cyberpunk judge mascot vector illustration
│   └── og-image.svg    # Open Graph 1200x630 social share banner
├── robots.txt          # Search engine crawler directives
├── sitemap.xml         # XML sitemap
├── .nojekyll           # GitHub Pages static asset bypass
├── vercel.json         # Vercel security headers and caching configuration
└── README.md           # This file
```

---

## 🛠️ How to Customize Demo Scenarios

All interactive terminal scenarios live in a single file: [`web/js/scenarios.js`](file:///c:/Users/vedan/Downloads/mltry/web/js/scenarios.js).

To edit or add a scenario:
1. Open [`js/scenarios.js`](file:///c:/Users/vedan/Downloads/mltry/web/js/scenarios.js).
2. Each scenario object follows this schema:
   ```javascript
   {
     id: "my-scenario-id",
     label: "🔥 My Custom Smell",
     badge: "REJECTED", // or "APPROVED"
     score: 3.5, // 0.0 to 10.0
     diff: `diff --git a/foo.py b/foo.py ...`,
     issues: [
       {
         severity: "HIGH", // "HIGH" | "MED" | "LOW"
         file: "foo.py",
         line: 12,
         problem: "Explanation of the issue",
         fix: "Actionable technical remediation"
       }
     ],
     roasts: {
       mild: "Gentle reminder.",
       spicy: "Clever sarcastic roast.",
       savage: "Brutal teardown."
     }
   }
   ```
3. Add the corresponding tab button in `index.html` under the `#scenario-pills` container if adding a new scenario.

---

## 🚀 Deployment Guide

### 1. GitHub Pages (Free)
1. In your GitHub repository settings, navigate to **Pages** (under Code and automation).
2. Under **Build and deployment > Source**, select **Deploy from a branch**.
3. Choose branch `main` and folder `/docs` or `/root` (if using root, point to where `index.html` is located, or deploy the `web/` folder).
4. The `.nojekyll` file is already included to ensure all assets serve properly.

### 2. Vercel (Free)
1. Push your repository to GitHub.
2. Go to [vercel.com/new](https://vercel.com/new) and import the repository.
3. In the project settings:
   - **Root Directory**: `web`
   - **Framework Preset**: `Other`
   - **Build Command**: None (leave empty)
   - **Output Directory**: None (leave empty)
4. Click **Deploy**. Security headers and caching are automatically configured via `vercel.json`.

### 3. Netlify (Free)
1. Drag and drop the `web/` folder directly into [app.netlify.com/drop](https://app.netlify.com/drop), or connect your Git repo.
2. Set **Publish directory** to `web`.
3. Deploy!

---

## 👤 Author & Repository

- **Author**: Vedant Raj ([@vedant29-code](https://github.com/vedant29-code))
- **Repository**: [https://github.com/vedant29-code/Git-Gud](https://github.com/vedant29-code/Git-Gud)
- **License**: MIT (Vedant Raj)
