# App

## Stainless OpenAPI generator

```bash
brew install stainless-api/tap/stl
stl auth login
stl init
```

* <https://app.stainless.com/inty/inty/overview> Stainless OpenAPI SDK generation project.

[Stainless core concepts](https://www.stainless.com/docs/guides/configure#core-concepts)

* Methods are invoked for actual APIs [defined in YAML](stainless.yml)
* Models are types reused throughout the SDKs
* Resources are a collection actual artifacts used in Client code.

There are 3 phases on Stainless:

1. Generate SDK, pushed to Stainless' internal github repo
2. Push to our own repo from Stainless' internal github repo
3. [Do not use] Push to language specific registry (pip/npm/maven)

<img width="800" height="1150" alt="image" src="https://github.com/user-attachments/assets/8c9c6098-921f-4c7e-a409-bc460805424c" />

You can trigger build on stainless.com by uploading your new openapi.json
to Stainless studio.

Or using stl cli with stainless.yml matches stainless studio's configs.

### Python SDK

```bash
pip install git+ssh://git@github.com/NascentCore/inty-python.git/
```

### Typescript

### Kotlin

## Deployment

* Run [build_and_deploy.yml](../.github/workflows/build_and_deploy.yml)
  to deploy the app to production server
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
