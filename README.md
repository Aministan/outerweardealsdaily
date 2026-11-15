# OuterwearDealsDaily

Static deal pages for jackets, parkas, and boots. Owned by Amin Peracha.

- `data/links.json` is the only place outbound product URLs live. Each product is keyed by slug. `price` stays null when the merchant page did not show a number. A CJ product feed can fill `price`, `compare_at`, and `price_checked` later.
- `merchants.<id>.deep_link` stays null until that CJ program is approved. The build then wraps the product URL and adds `sid` as `{pagetype}-{slug}-{placement}`. While it is null, buttons are the plain product URL with no tracking parameters.
- `scripts/build.py` writes `site/`. It refuses tracking hosts and does not request them.
- `scripts/links.py` is the SID and click-URL helper. Checks are string checks only.

```bash
python3 scripts/build.py
```

Environment:

- `SITE_URL` origin, default `https://outerweardealsdaily.com`
- `PATH_PREFIX` default empty

The Pages workflow builds with that origin and an empty prefix. The custom domain is set in the repository Pages settings. Do not add a CNAME file unless a deploy removes the domain.

GitHub Pages deploys from `.github/workflows/pages.yml` on every push to `main`.

Prices in this repo were read from merchant product pages on 2026-11-15. Sorel Explorer product URLs we tried resolved to the Sorel homepage, so there is no Explorer deal page until a live product URL is added to `data/links.json`.
