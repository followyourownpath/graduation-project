# Software Quality Acceptance Evidence

All evidence in this directory uses public pages, placeholder configuration or synthetic data. It contains no passwords, access tokens, customer records or service credentials.

| File | Acceptance case | Environment | Result |
|---|---|---|---|
| `AT-14-local-docker.txt` | AT-14 | Local Docker Engine 29.5.3, base revision `0c72994` | Backend healthy and frontend login returned HTTP 200 |
| `AT-14-local-docker-login.png` | AT-14 | Locally built production containers | Login page rendered without console errors or horizontal overflow |
| `AT-17-login-desktop.png` | AT-17 (public login surface) | `https://aimeshlabs.au/bread/login`, 1440 x 900 | Primary login action visible and layout unclipped |
| `AT-17-login-mobile.png` | AT-17 (public login surface) | `https://aimeshlabs.au/bread/login`, 390 x 844 | Primary login action visible; document width matched viewport width |

Authenticated workflow screenshots must be added only after the nominated assessor account is available. Use synthetic records and redact identifiers before committing any additional evidence.
