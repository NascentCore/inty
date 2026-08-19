<!-- CREATED_BY_AGENT -->

# 2026-08-19 Production outage post-mortem

Two stacked failures: the GCE VM became unreachable at the application layer because the boot disk was full, then after restore Android chat still failed because the OpenRouter account had no credits.

Follow-up issues: [issues/3887](https://github.com/NascentCore/inty/issues/3887), [issues/3888](https://github.com/NascentCore/inty/issues/3888), [issues/3889](https://github.com/NascentCore/inty/issues/3889), [issues/3890](https://github.com/NascentCore/inty/issues/3890).

Day-of recovery notes: [rollback_records/2026-08-19-enospc-recovery.md](../rollback_records/2026-08-19-enospc-recovery.md). Live container map: [DEPLOYMENT_STATE.md](../DEPLOYMENT_STATE.md).

## Impact

- **Duration (VM)**: userspace stall until 2026-08-19 ~20:08 UTC reboot. Disk had been full for weeks (serial `No space left on device`; last human-readable syslog before that was May). Public symptoms reported 2026-08-19.
- **Duration (chat after restore)**: ~20:11-20:36 UTC. HTTP API was up; completions returned 500 until OpenRouter credits were added.
- **Who**: IntelliMate Android (`okhttp` to `app.inty.cc`), web `intellimate.app` (API proxied to the same backend), Ops HTTPS (`ops.inty.cc`, `dev.ops.inty.cc`). Static marketing sites timed out while nginx could not complete TLS.
- **What users saw**: App chat bubbles with a red bang and "Something went wrong. Please try again later."
- **Not in scope of the stall**: iMate containers were already stopped (expected 502). `inty-backend-dev` was already stopped.

## Timeline (UTC)

- **2026-05-17 22:20 -07:00**: last VM start before this incident (`prod-intellimate`, 4 vCPU / 8 GiB, 100 GiB `pd-standard`).
- **2026-07-02**: container logs moved from `gcplogs` to Docker default `json-file` with no size cap ([rollback 2026-07-02](../rollback_records/2026-07-02-disable-gcplogs-and-vm-state.md)).
- **~2026-07-10**: estimated start of ENOSPC (kernel timestamp ~52d after last boot).
- **2026-07-08 / 2026-08-18**: `dev.ops.inty.cc` and `intellimate.app` certificates expired (`certbot.timer` was enabled but could not write while the disk was full).
- **2026-07-29 onward**: `build_and_deploy_ops.yml` failing; sample run `30762646444` greps `devops/config.yaml.dev` **before** `actions/checkout`.
- **2026-08-19 (cloud agent)**: ping and TCP 22/80/443 succeed; HTTPS/SSH time out; no SSH key on that agent. Recon only.
- **2026-08-19 ~19:55-20:08**: this session: SSH banner timeout; serial console ENOSPC; snapshot `prod-intellimate-enospc-20260819`; disk resize 200 GiB; instance reset; filesystem ~194 GiB, ~35% used.
- **20:08-20:11**: `inty-ops-*` and `inty-pg` healthy; `inty-backend-prod` exit 127 because `/tmp/inty-backend-start.sh` vanished on reboot (Docker created a directory). Restored script under `/opt/inty-prod/` and recreated the container.
- **20:20-20:21**: Android `POST /api/v1/chat/completions/...` HTTP 500. Backend log: OpenRouter **402 Insufficient credits**.
- **~20:36**: same agent HTTP 200 after credits added. User confirmed Android chat works.

## Root causes

1. **ENOSPC**: unbounded Docker `json-file` logs plus journal growth filled a 100 GiB disk. Kernel still accepted TCP; sshd and nginx did not complete banners/handshakes. Detection was human ("backend seems down"), not disk alerts.
2. **OpenRouter account empty**: independent of the VM. Completions mapped provider 402 to HTTP 500; the Android client always toasts the generic string. A small top-up left about $10 remaining at check time -- this will fail again without a balance alert.
3. **Amplifiers**:
   - Prod `start.sh` bind-mounted from `/tmp` (lost on reboot).
   - Docs still called the instance `dev-instance`; the running instance name is `prod-intellimate` (disk name remains `dev-instance`). Cloud agent could not SSH.
   - Ops CI could not redeploy (checkout order).
   - Certbot `renew` also fails on dead DNS names, so a live-cert failure is easy to miss in a noisy non-zero exit.

## Working logs reviewed

- GCE serial port: `systemd-journald: No space left on device`.
- `ssh inty`: `docker ps`, reclaim script `/var/log/inty-enospc-reclaim.log`, `/opt/inty-prod/inty-backend-start.sh`.
- nginx `access.log`: okhttp completions 500 then 200; unauthenticated probes 401.
- Backend json logs (including `.1` after logrotate): OpenRouter 402 traceback; later completions 200. `sudo docker logs` hung after `copytruncate` -- read files under `/var/lib/docker/containers/` instead.
- OpenRouter `GET /api/v1/credits` (key never written into this doc): `total_usage` at the credit ceiling, then a small remaining balance after top-up.
- GitHub Actions: Ops workflow assert step before checkout.

## What went well

- ICMP/TCP vs banner-timeout split the failure to "userspace stuck", not "VM deleted".
- Serial console still worked when SSH did not.
- Snapshot before resize.
- Android failure was confirmed on the same request path (agent id + 500 body size 791) rather than guessed as "still down".

## What went poorly

- No disk-usage page.
- json-file adopted without `max-size`.
- `/tmp` used for a bind-mount that must survive reboot.
- Provider quota surfaced as "backend error".
- `docker logs` became unusable right after we force-rotated logs.

## Action items

- [issues/3887](https://github.com/NascentCore/inty/issues/3887): apply json-file caps to running containers, fix `docker logs` after rotate, disk alert.
- [issues/3888](https://github.com/NascentCore/inty/issues/3888): OpenRouter credit alert + 402 mapping (human still owns topping up `it@sxwl.ai`).
- [issues/3889](https://github.com/NascentCore/inty/issues/3889): Ops deploy workflow: checkout before config grep.
- [issues/3890](https://github.com/NascentCore/inty/issues/3890): delete dead certbot lineages; live TLS failure must page.
- Commit the in-repo devops doc updates from this incident (`DEPLOYMENT_STATE.md`, this post-mortem, rollback record) when ready.

## OpenRouter (human)

Keep the prod OpenRouter account funded. About $10 remaining after the 2026-08-19 top-up is not a production buffer.
