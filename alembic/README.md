# Alembic

## Generate version

* `alembic upgrade head`: run this to make sure the local database is in sync with the newest version
* `alembic revision --autogenerate --message "<write your message for this version>": this will write the new version script for you
* `alembic upgrade head`: run this again to apply your new version file
* If the above failed, you'll need to debug with @yaxiong on why this failed
* If you want to redo the newest version, first rollback the local changes with `alembic downgrade -1` and then delete the new version
  file you generated with `alembic revision --autogenerate --message "<...>"`, and then recreate the version file, by rerunning
  `alembic revision --autogenerate --message "<...>"`.

## SOPs

### Manually set alembic_version when 

* `alembic_version` table has a single row, writes the newest version applied to the database.
* You can update its value to the newest version number: `insert into alembic_version (version_num) values ('75796d073cb2');`
* Afterwards the revisions will be applied after the recorded version
