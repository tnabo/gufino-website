# gufino.com

Static site for **Gufino Bilingual Learning**, hosted free on GitHub Pages. Replaces the Shopify store; every "Buy" button goes to the product's Amazon listing.

## How it works

| Path | What it is |
|---|---|
| `data/catalog.json` | **Edit this.** Products shown, their collection, Amazon ASINs, flash-card colors, redirects, social links |
| `data/shopify_products.json` | Product titles, descriptions and image list (imported once from Shopify) |
| `data/policies/*.html` | Privacy / refund / shipping / terms (imported once from Shopify) |
| `static/` | CSS, JS, and all images (imported once from Shopify) |
| `build.py` | Generates the site into `_site/` |
| `tools/import_shopify.py` | One-time import from the live Shopify store |
| `.github/workflows/deploy.yml` | Builds and publishes on every push to `main` |

The first push runs the Shopify import automatically on GitHub's servers and commits the images and data back to the repo. **Do this before cancelling Shopify.**

URLs match the old Shopify ones (`/products/...`, `/collections/...`, `/pages/...`, `/policies/...`), so existing links and Google rankings carry over. Old duplicate flash-card URLs redirect to the merged product with the right color selected.

## Common edits

- **Change an Amazon link:** edit the `asin` in `data/catalog.json`.
- **Add a product:** add its entry to `catalog.json` and its data to `shopify_products.json` (title, `body_html`, images) plus images in `static/images/products/<handle>/1.jpg, 2.jpg…`.
- **Preview locally:** `python build.py && python -m http.server -d _site 8000`

## Going live (one time)

1. Repo → Settings → Pages → Source: **GitHub Actions**.
2. Push to `main` (or Actions → "Build & deploy site" → Run workflow). Wait for the green check.
3. Settings → Pages → Custom domain: `www.gufino.com` → Save.
4. At the domain's DNS provider:
   - `CNAME` record: `www` → `tnabo.github.io`
   - `A` records for the bare domain `gufino.com`: `185.199.108.153`, `185.199.109.153`, `185.199.110.153`, `185.199.111.153`
   - Remove the old Shopify records (`CNAME www → shops.myshopify.com`, `A @ → 23.227.38.65`).
5. Once the certificate is issued, tick **Enforce HTTPS**.
6. Only after the new site is live and the images are in the repo: remove the domain from Shopify and close the store.
