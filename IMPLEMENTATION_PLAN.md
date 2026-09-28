# LLK Analytics implementation handoff

## Goal and guardrails

Modernize the Django application without changing its information architecture or removing existing pages. Preserve the current public routes and their page purposes:

- `/`, `/services/`, `/contact/`
- `/blog/` and date-based blog detail URLs
- `/courses/`, category-filtered course URLs, course details, and cart URLs

The finished site must use PostgreSQL for published blog and course data, allow that data to be administered through Django admin, deliver contact messages through configured SMTP, and deploy with the same Docker/Caddy/GitHub Actions pattern used by `../llkmusic`.

Do not add payment processing in this work. The existing cart remains a session cart and its behavior is unchanged.

## Current-state facts to preserve or repair

1. `blog.models` already defines `Post` and `Comment`, but `blog/migrations/` is missing. Blog records therefore cannot be reliably provisioned by source-controlled migrations.
2. `courses.models` already defines `Category` and `Course`, with two existing migrations. Tighten the model constraints in a new migration; do not recreate the course tables.
3. The app hard-codes a PostgreSQL password, Django secret key, `DEBUG=True`, and an open host list. Replace all with environment configuration.
4. The contact view reports success even if `send_mail()` raises. It currently uses Django's file email backend rather than a production email provider.
5. `STATIC_ROOT` points to the source `static/` directory in production. Change it to a separate `staticfiles/` directory so `collectstatic` never overwrites source assets.

## Phase 0 — preflight and data safety

1. Create a feature branch and take a tested PostgreSQL backup of any live LLK Analytics database before applying migrations.
2. Inspect the live schema and row counts for `blog_post`, `blog_comment`, `courses_category`, and `courses_course`.
3. Determine whether the live blog tables exactly match Django's first generated migration.
   - If this is a new database, apply migrations normally.
   - If tables already exist and match the initial migration, use `migrate --fake-initial` once, then apply later migrations normally.
   - If tables differ, write a one-off data/schema migration after a backup; never use `--fake` blindly.
4. Add `.env.example`; keep `.env` ignored. Do not commit passwords, SMTP app passwords, or SSH keys.

## Phase 1 — make PostgreSQL the supported persistence layer

### Settings and dependencies

1. Upgrade Django to a maintained version compatible with the chosen Python image (mirror LLKMusic's supported range, or use the current project-approved Django LTS) and add:
   - `dj-database-url`
   - `gunicorn`
   - `psycopg[binary]` (replace `psycopg2-binary`)
   - retain `whitenoise`, `Pillow`, `django-summernote`, and `django-honeypot`
2. Refactor `llkanalytics/settings.py` to use helper functions equivalent to LLKMusic's `env_bool` and `env_list`.
3. Configure the database exclusively from `DATABASE_URL` in deployed environments, with connection reuse and health checks. A local SQLite fallback is acceptable only for an explicitly documented no-Docker developer workflow; Docker and CI must use PostgreSQL.
4. Move these values to environment variables: `SECRET_KEY`, `DEBUG`, `ALLOWED_HOSTS`, `CSRF_TRUSTED_ORIGINS`, `SITE_URL`, `MEDIA_ROOT`, cookie/HTTPS settings, database URL, and all email settings.
5. Add WhiteNoise immediately after `SecurityMiddleware`; set `STATIC_ROOT = BASE_DIR / 'staticfiles'`; retain `STATICFILES_DIRS = [BASE_DIR / 'static']`; use compressed WhiteNoise storage in production.
6. Set production-safe security defaults through environment variables: HTTPS proxy header, secure session/CSRF cookies, SSL redirect, and HSTS. Keep development defaults usable locally.

### Blog models and migrations

Keep the public URL shape and the existing `Post`/`Comment` concepts. Implement these model contracts in `blog/models.py`:

| Model | Required persisted fields and rules |
| --- | --- |
| `Post` | `title`, `slug`, `author` (FK to user), rich `body`, `publish`, `created`, `updated`, draft/published `status`; ordering by newest publish date; published manager; indexes for publish/status and date URL lookups. |
| `Comment` | `post` FK, `name`, `email`, `body`, `created`, `updated`, `active`; ordering and index by `created`. |

Implementation details:

1. Generate and commit `blog/migrations/0001_initial.py` from the present models, after Phase 0's schema decision.
2. Add a follow-up migration/model change only when needed to make the date-based slug lookup unambiguous. Preferred: retain `slug` plus `unique_for_date='publish'`, because the URL already contains the date. Do **not** change detail URLs to a new shape.
3. Add a compound index matching the public detail query (`status`, `publish`, `slug`) if PostgreSQL query inspection shows it is useful; keep the existing newest-first index.
4. Keep Summernote administration for `body`; retain list filters, search, pre-populated slug, and author selection. Ensure only published posts are visible publicly and comments remain moderator-controlled through `active`.
5. Add optional `excerpt` and `featured_image` only if the approved visual implementation needs them. Both must be nullable/blank so existing posts render without a data backfill. They are not prerequisites for PostgreSQL integration.

### Course models and migrations

Retain the current course list, category filtering, detail pages, image upload, price, availability flag, and session cart. In a new migration after `courses.0002`:

1. Make `Course.slug` globally unique because detail views resolve it without category context. Before adding the constraint, detect and rename duplicates deterministically; record that mapping in the migration or a one-time management command.
2. Add a database `CheckConstraint` requiring `price >= 0` and a matching `MinValueValidator`.
3. Keep `Category.slug` unique and the `Category -> Course` relationship. Preserve `on_delete=CASCADE` unless the product owner explicitly prefers preventing deletion of a populated category.
4. Keep `name`, `slug`, `image`, `description`, `price`, `available`, `created`, and `updated` field names so the existing templates, cart, admin, and sitemap work without page changes.
5. Keep the current indexes and add an availability/listing index only after validating it with PostgreSQL `EXPLAIN`; do not add speculative indexes.
6. Confirm the course admin remains the source of truth, with searchable course names/descriptions and category filtering. Use `list_select_related` where it avoids N+1 queries.

### Query/view rules

1. Use `select_related('category')` in course list/detail queries where the template reads the category.
2. Use `.only()` only if profiling confirms a benefit; prioritise clear code.
3. Replace invalid page numbers in blog pagination with Django's graceful `get_page()` behavior.
4. Preserve template names, context keys, route names, SEO tags, sitemap entries, and existing page copy unless the visual phase needs wrapper/class changes.

## Phase 2 — wire the contact form correctly

Keep `/contact/` as a standalone page. Mirror LLKMusic's delivery behavior rather than moving the form to the home page.

1. Replace `EmailPostForm` with a clearly named `ContactForm`:
   - `name`: 100-character maximum
   - `email`: Django `EmailField`
   - `service`: optional/select field for Analytics consulting, Data/BI project, Training/course, Speaking/other
   - `message`: required, 10–3,000 characters
   - `website`: hidden honeypot field
2. Use one honeypot approach. Prefer the explicit hidden `website` field and `clean_website()` pattern from LLKMusic; remove the redundant package decorator/template tag if it is no longer used. Do not reject normal messages merely because they contain a URL.
3. Make the contact view a `FormView` or retain a small function view with equivalent behavior:
   - on valid POST, construct `EmailMessage` with a useful subject, form body, `DEFAULT_FROM_EMAIL`, `CONTACT_FORM_RECIPIENTS`, and `reply_to=[visitor email]`;
   - call `send(fail_silently=False)`;
   - on success, add a Django success message and redirect to `/contact/#contact` (POST/Redirect/GET);
   - on SMTP failure, log the full exception, keep the entered form values, render a clear error message, and return a non-success response—never claim delivery;
   - on invalid input or honeypot trigger, send no mail.
4. Add settings from LLKMusic's pattern: `EMAIL_BACKEND`, host, port, TLS, timeout, credentials, `DEFAULT_FROM_EMAIL`, and comma-separated `CONTACT_FORM_RECIPIENTS`.
5. Update the template to render `messages`, per-field errors, accessible labels, `autocomplete` attributes, and an `aria-live` status region. Preserve the existing contact page content and route.
6. For local development use console email; for production set a real SMTP provider/app password in the server `.env`. Verify delivery and Reply-To using a real test inbox after deployment.

## Phase 3 — AI-themed visual refresh, without changing pages

Adopt a restrained **"Analyst's Neural Console"** theme. It should read as trustworthy data work, not a generic sci-fi dashboard.

1. Move the scattered inline styling from base, home, blog, courses, and contact templates into semantic classes in `static/css/style.css`; keep the current DOM content and routes. Introduce design tokens for ink/navy surfaces, off-white content, cyan as the primary signal, violet as the secondary signal, and a high-contrast success color.
2. Upgrade the shared shell: subtle dark gradient/nav, thin cyan active-link indicator, a small `LLK // ANALYTICS` wordmark treatment, consistent max-width container, and a cleaner responsive mobile menu. Make the existing search form either functional or remove it; do not leave a non-submitting fake control.
3. Add an unobtrusive hero background to the home page using CSS/SVG only: a low-opacity dot matrix/data-grid and a few linked-node lines behind the existing photo and introduction. It must be decorative (`aria-hidden`), static by default, and have no impact on readability.
4. Restyle blog rows and course cards as "signal cards": dark/cyan metadata chip, elevated hover/focus state, readable excerpts, consistent image aspect ratio, and a visible keyboard focus ring. Do not require new images; retain current fallback images.
5. Give article/course detail pages a compact metadata rail and a code/data-friendly typography treatment (comfortable line length, polished `pre`/table styles, MathJax-compatible content). Do not change article bodies or course descriptions.
6. Make the contact form a clear console-like panel with a one-sentence service selector, labelled inputs, valid/error/success states, and a button loading/disabled state only if implemented accessibly.
7. Respect `prefers-reduced-motion`, meet WCAG AA contrast, ensure keyboard navigation remains visible, preserve meaningful image alt text, and test at 320px, 768px, and desktop widths. No autoplay, flashing effects, or canvas/WebGL dependencies.

## Phase 4 — deployment parity with LLKMusic

Copy the deployment architecture, replacing project/domain names only:

1. Add `Dockerfile` using a supported slim Python image, install requirements, copy the project, run the existing-style entrypoint, and start Gunicorn on port 8000.
2. Add `entrypoint.sh` to run `migrate --noinput` and `collectstatic --noinput` before Gunicorn.
3. Add `docker-compose.yml` for local development: `web` plus PostgreSQL 16, database healthcheck, source bind mount, and named volumes for PostgreSQL and media.
4. Add `docker-compose.prod.yml`: Gunicorn web service, PostgreSQL, Caddy reverse proxy with ports 80/443, named persistent media/PostgreSQL/Caddy volumes, and no exposed database port.
5. Add a project-specific `Caddyfile` serving `/static/*` from the collected static volume/location and `/media/*` from the persistent media volume, proxying remaining requests to `web:8000`, and managing TLS for `llkanalytics.com`/`www.llkanalytics.com` as appropriate.
6. Add `.env.example` documenting every required variable, especially `DATABASE_URL` (or compose-derived equivalent), PostgreSQL credentials, domain hosts/origins, SMTP credentials, and security settings.
7. Add `scripts/deploy-production.sh`, modeled on LLKMusic: validate `.env`, verify a clean deploy checkout, fetch the configured deploy branch, build/restart Compose services, show status, and prune build cache. Do not include secrets in this script.
8. Add `.github/workflows/deploy.yml` with:
   - a PostgreSQL service test job;
   - dependency installation, `makemigrations --check --dry-run`, `migrate`, `check`, and test execution;
   - deploy only after tests pass, via encrypted SSH secrets;
   - a retrying HTTPS smoke check for the home page and one dynamic route.
9. Before DNS cutover, provision the server checkout, `.env`, firewall/ports 80+443, Docker, SSH deploy key, and backup schedule. Verify Caddy can obtain certificates and that media persists across a container rebuild.

## Phase 5 — tests and acceptance checks

Add real tests before declaring completion. At minimum:

1. Model tests: published-manager visibility, post date/slug URL, comment ordering/active visibility, course category URL, unavailable course hidden, non-negative price constraint, and duplicate-course-slug rejection.
2. View tests: all existing public routes return expected responses, blog invalid pagination is graceful, correct content visibility, and sitemap only includes public records.
3. Contact tests copied/adapted from LLKMusic: valid submission sends one email to configured recipients with visitor email as Reply-To; invalid/honeypot submission sends none; SMTP failure renders an error rather than a success message.
4. Settings/deployment checks: environment-driven settings work in CI, `collectstatic --noinput` succeeds, migrations are committed, Docker Compose starts against PostgreSQL, and `python manage.py check --deploy` passes with production-like environment values.
5. Manual browser checks: page routes/content remain in place, admin can create and publish a post/course, media uploads render, responsive navigation works, visual focus/contrast meet the Phase 3 rules, contact delivery reaches the intended mailbox, and a production redeploy preserves database and media data.

## Implementation order for a smaller model

1. Add env configuration, dependencies, `.env.example`, and safe static/media settings; write tests that establish the intended configuration.
2. Commit blog initial migration and course constraint migration; run against a disposable PostgreSQL database and then follow Phase 0 for production data.
3. Make the smallest query/admin fixes and test routes/sitemaps.
4. Implement and test contact delivery end-to-end with the local-memory email backend.
5. Build the CSS/template visual refresh without altering URL names, page copy, or business behavior.
6. Add Docker/Compose/Caddy/deploy workflow, validate it locally, then provision production secrets and deploy.

Every phase should be a separate reviewable commit. Stop at the Phase 0 decision gate if a live database schema does not match the generated migrations; that is the one point where an implementation agent must not make an assumption.
