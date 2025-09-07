# App

## Stainless OpenAPI generator

```bash
brew install stainless-api/tap/stl
stl auth login
stl init
pip install git+ssh://git@github.com/NascentCore/inty-python.git/
```

## Deployment

* Run [deploy_prd.yml](../.github/workflows/deploy_prd.yml) to deploy the app to production server
* Open Google Cloud Console, login with `it@sxwl.ai` (or your own account)
* Open Compute Engine, and find `dev-intance`
* `/etc/nginx/conf.d/sxwl.ai.conf` has the host's nginx config

* Launch postgres with pgvector extensions

```bash
docker run --name dev-postgres \
    -e POSTGRES_USER=postgres \
    -e POSTGRES_PASSWORD=postgres \
    -p 5432:5432 \
    -d pgvector/pgvector:pg16

# Login with psql
psql -h localhost -U postgres
> \l # List all databses
> DROP DATABASE <db>; # Drop database
# Drop all connections to the database
> SELECT pg_terminate_backend(pg_stat_activity.pid)
FROM pg_stat_activity
WHERE pg_stat_activity.datname = 'inty_prd'
  AND pg_stat_activity.pid <> pg_backend_pid();

createdb -h localhost -U postgres inty_prd
alembic upgrade head
```

* If alembic shows multiple heads error, you can delete the heads shown by `alembic show heads`

* Install alembic and update database `alembic upgrade head`
