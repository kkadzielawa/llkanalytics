# Website review — November 8, 2026

## Implemented

- Replaced spoofable `X-Forwarded-For` handling. Direct requests use the actual
  peer address. Production Caddy overwrites `X-LLK-Client-IP`; production Compose
  explicitly enables trust in that header and does not expose the web port.
- Moved public form limits to PostgreSQL-backed counters with transactions,
  row locks, and unique keys. Limits survive worker changes and container
  restarts: 10 attempts per IP and 3 valid submissions per IP/email in 15 minutes,
  independently for contact and comments. Invalid requests count as attempts.
  The throttle table stores keyed hashes, counts, and expiry times; expired rows
  are removed in bounded batches during subsequent submissions.
- Added unique, signed, expiring, single-use tokens and minimum completion time
  to both forms. Kept honeypots and the existing two-link allowance. Comments
  are limited to 3,000 characters and remain subject to moderation.
- Added explicit 429 responses with `Retry-After`, preserved form values on
  errors, and recoverable token errors. Successful comments redirect to the
  article so refreshing the page does not repost. Token reuse cannot resend a
  contact email or create another comment.
- Contact delivery now requires the mail backend to report one accepted message.
  A failure returns 503, keeps the visitor's input, and releases the token for
  retry. Visitors remain in Reply-To; the configured sender and recipients are
  never taken from request parameters. Names cannot inject email headers.
- Restricted Summernote attachment uploads to active staff accounts. The
  package default previously permitted anonymous uploads. Kept its original
  primary-key type to avoid an unrelated third-party migration.
- Upgraded Django 4.2.23 to 5.2.19 LTS and patched python-dotenv, soupsieve, and
  sqlparse after a vulnerability audit. Removed the unused honeypot dependency.
  Added dependency auditing to CI and pip updates to the Docker build.
- Installed admin/editor assets now take precedence over old collected copies
  checked into `static/`. Production refuses the known default/placeholder
  Django signing secret.
- Added a skip link, accessible field error associations, Escape/outside-click
  menu dismissal, mobile navigation without JavaScript, long-content wrapping,
  a services-to-contact call to action, and a course empty-state contact link.
  Course list images load lazily. Blog excerpts render as plain text and no
  longer load MathJax; full articles retain it.

## Verification

- Django suite: 44 tests, 43 passed and one PostgreSQL-specific concurrency test
  skipped on local SQLite. CI already uses PostgreSQL 16, where that test runs.
- All migrations applied successfully to a disposable SQLite database.
- `makemigrations --check --dry-run`: no changes detected.
- `check --deploy` with production-like security settings: no issues.
- Dependency audit after patching: no known vulnerabilities found in the
  installed environment. This is a point-in-time check, not a security guarantee.
- Static collection completed; current admin asset selection is regression-tested.
- Browser access was unavailable, so responsive layout and keyboard interactions
  still need visual verification at 320px, 768px, and desktop widths. No live
  SMTP delivery, production deployment, or production database changes were made.

## Domain email protection still to configure

Public DNS queries through Google's resolver on November 8 returned no TXT
answers at `llkanalytics.com` and NXDOMAIN for `_dmarc.llkanalytics.com`.
No apex SPF record or DMARC record was found. DKIM cannot be inferred without
the mail provider's selector. These records are managed at the DNS/mail provider,
not by this Django application.

1. Identify all services sending as `@llkanalytics.com`, including the website's
   SMTP provider. Publish one SPF record authorizing those actual senders.
2. Enable DKIM at each sender and publish the provider-issued DNS records.
3. Start DMARC reporting with a monitored destination, confirm legitimate mail
   authenticates and aligns, then move to quarantine/reject. Do not publish a
   guessed SPF include or an enforcing DMARC policy before checking senders.
4. Enable the mailbox provider's spam/phishing filtering and report unwanted
   messages there. Domain authentication protects against spoofing and helps
   delivery; it does not filter every unwanted message arriving in an inbox.

References: [Google email authentication guidance](https://support.google.com/mail/answer/81126),
[Cloudflare DNS email records](https://developers.cloudflare.com/dns/manage-dns-records/how-to/email-records/),
[Django supported releases](https://www.djangoproject.com/download/),
[Caddy proxy header behavior](https://caddyserver.com/docs/caddyfile/directives/reverse_proxy#headers).

## Deployment notes

Deploy through the existing workflow. Its entrypoint runs the new
`pages.0001_initial` migration and collects static assets. The migration only
adds the throttle table; it does not modify blog/course data. Keep the existing
database backup routine before applying production changes.

Ensure production has a unique `SECRET_KEY`, working SMTP credentials, the
correct sender/recipients, and `DEBUG=False`. Keep
`CONTACT_FORM_MIN_SECONDS=3` and `COMMENT_FORM_MIN_SECONDS=3` unless changing
them deliberately. With the supplied Compose file, only Caddy should be reachable
from the internet; `TRUST_PROXY_CLIENT_IP=True` is unsafe for directly exposed
application servers. A CDN or load balancer added in front of Caddy needs a
separate review of its trusted-proxy configuration.

Local validation can use `DEBUG=True` and SQLite without touching production.
Concurrency protection is intended for the supported production PostgreSQL
configuration; SQLite does not implement `SELECT FOR UPDATE`.
