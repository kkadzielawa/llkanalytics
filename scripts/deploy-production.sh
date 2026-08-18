#!/bin/sh
set -eu

PROJECT_DIR=${PROJECT_DIR:-/srv/llkanalytics}
DEPLOY_BRANCH=${DEPLOY_BRANCH:-main}

if [ ! -f "$PROJECT_DIR/.env" ]; then
    echo ".env file is required in $PROJECT_DIR"
    exit 1
fi

cd "$PROJECT_DIR"

if [ -n "$(git status --porcelain)" ]; then
    echo "Deploy checkout must be clean before deploying."
    exit 1
fi

git fetch origin "$DEPLOY_BRANCH"
git checkout "$DEPLOY_BRANCH"
git reset --hard "origin/$DEPLOY_BRANCH"

docker compose -f docker-compose.prod.yml --env-file .env build
docker compose -f docker-compose.prod.yml --env-file .env up -d
docker compose -f docker-compose.prod.yml --env-file .env exec -T web python manage.py shell -c "from urllib.parse import urlparse; from django.conf import settings; from django.contrib.sites.models import Site; parsed = urlparse(settings.SITE_URL); domain = parsed.netloc or parsed.path; Site.objects.update_or_create(id=settings.SITE_ID, defaults={'domain': domain, 'name': 'LLKAnalytics'}); print(f'Synced django_site to {domain}')"
docker compose -f docker-compose.prod.yml --env-file .env ps
docker image prune -f
