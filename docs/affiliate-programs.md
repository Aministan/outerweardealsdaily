# Affiliate programs

CJ applications are pending. Commission figures below are the rates to use once the program shows them. Frye's rate was not provided, so it is left blank. Do not request a click URL. Price checks use the plain product page in `data/links.json`.

- Columbia — CJ advertiser 2844548, 8%.
- Sorel — CJ advertiser 2854924, 8%.
- Canada Goose — CJ advertiser 5511596, 5%.
- Hunter Boots — CJ advertiser 6578297, 4%.
- Dr. Martens US — CJ advertiser 5241344, 4%.
- Thursday Boot Company — CJ advertiser 6533705, 4.5%.
- Frye — CJ advertiser 5111696. Commission rate is whatever CJ shows after approval.

Xtratuf and Muck Boot Company are linked with plain product URLs. No program is on file.

Patagonia (Down Sweater, Better Sweater), The North Face (1996 Retro Nuptse), and UGG are comparison names only. No buy link.

When a program is approved, set `merchants.<id>.deep_link` in `data/links.json` to that program's CJ click base (`/click-<publisher>-<ad>`). Leave every product `url` as the plain merchant page. The build adds `sid`.
