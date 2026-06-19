# One-shot pg_upgrade image with pgvector on both PG16 (old) and PG17 (new) bindirs.
# CREATED_BY_AGENT
FROM pgvector/pgvector:pg16 AS pg16
FROM pgvector/pgvector:pg17
COPY --from=pg16 /usr/lib/postgresql/16 /usr/lib/postgresql/16
COPY --from=pg16 /usr/share/postgresql/16 /usr/share/postgresql/16
ENV PGDATAOLD=/var/lib/postgresql/16/data \
    PGDATANEW=/var/lib/postgresql/17/data
COPY docker-upgrade /usr/local/bin/docker-upgrade
ENTRYPOINT ["docker-upgrade"]
CMD ["pg_upgrade", \
  "-b", "/usr/lib/postgresql/16/bin", \
  "-B", "/usr/lib/postgresql/17/bin", \
  "-d", "/var/lib/postgresql/16/data", \
  "-D", "/var/lib/postgresql/17/data"]
