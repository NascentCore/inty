# Alembic

## Generate version

* `alembic upgrade head`: run this to make sure the local database is in sync with the newest version
* `alembic revision --autogenerate --message "<write your message for this version>": this will write the new version script for you
* `alembic upgrade head`: run this again to apply your new version file
* If the above failed, you'll need to debug with @yaxiong on why this failed
* If you want to redo the newest version, first rollback the local changes with `alembic downgrade -1` and then delete the new version
  file you generated with `alembic revision --autogenerate --message "<...>"`, and then recreate the version file, by rerunning
  `alembic revision --autogenerate --message "<...>"`.
