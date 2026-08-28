# Referensi Instalasi — BKPM HA Stack (bkpm-ha-v2)

Dokumen referensi tunggal untuk stack HA BKPM: PostgreSQL, Valkey, RabbitMQ.
Sumber: playbook `bkpm-ha-v2` + docs Obsidian `mastersystem/bkpm/`.

---

## 1. Node & IP

| Node       | IP              | VMID (Proxmox) | Peran                          |
|------------|-----------------|----------------|--------------------------------|
| pg-1       | 192.168.1.50    | 109            | PostgreSQL Leader (dinamis)    |
| pg-2       | 192.168.1.51    | 110            | PostgreSQL Sync Standby        |
| pg-3       | 192.168.1.52    | 111            | PostgreSQL Replica             |
| vk-1       | 192.168.1.53    | 112            | Valkey PRIMARY                 |
| vk-2       | 192.168.1.54    | 113            | Valkey REPLICA                 |
| vk-3       | 192.168.1.55    | 114            | Valkey REPLICA                 |
| rb-1       | 192.168.1.56    | 116            | RabbitMQ (basis cluster)       |
| rb-2       | 192.168.1.57    | 117            | RabbitMQ                       |
| rb-3       | 192.168.1.58    | 118            | RabbitMQ                       |

OS semua node: **Ubuntu 24.04** (Noble Numbat).

---

## 2. Versi Paket

| Komponen              | Versi              | Cara Install                              | Node            |
|-----------------------|--------------------|-------------------------------------------|-----------------|
| PostgreSQL            | 17                 | apt (repo PGDG)                           | pg-1/2/3        |
| postgresql-client     | 17                 | apt (repo PGDG)                           | pg-1/2/3        |
| etcd                  | 3.5.32             | binary GitHub → /usr/local/bin            | pg-1/2/3        |
| Patroni               | latest (pip, tidak di-pin) | pip venv `/opt/patroni-venv` (patroni[etcd3]) | pg-1/2/3  |
| psycopg2-binary       | latest (pip)       | pip venv `/opt/patroni-venv`              | pg-1/2/3        |
| PgBouncer             | versi apt Ubuntu 24.04 (live: 1.25.2) | apt | pg-1/2/3        |
| Valkey                | 9.1.1              | binary resmi valkey.io (noble x86_64) → /usr/local/bin | vk-1/2/3        |
| RabbitMQ Server       | 4.2.9-1 (LTS, pin exact) | apt (repo Team RabbitMQ deb1)        | rb-1/2/3        |
| Erlang                | 1:27.3.4.16-1 (OTP 27.x, pin exact) | apt (repo Team RabbitMQ Erlang) | rb-1/2/3        |

> Catatan: versi di-pin untuk etcd (3.5.32), Valkey (9.1.1), RabbitMQ (4.2.9-1),
> Erlang (1:27.3.4.16-1) — selain itu mengikuti repo pada saat eksekusi.
> Valkey: binary resmi valkey.io 9.1.1 (noble x86_64) — apt noble universe cuma punya 7.2.12,
> makanya pakai binary artifact (sha256 di-pin). Lab yang sudah jalan tetap 9.0.5 (compile).
> Patroni dipasang via pip dalam venv (PEP 668 Ubuntu 24.04 wajib venv).

---

## 3. Daftar Paket yang Diinstal

Sumber: task `ansible.builtin.apt` / `pip` / `get_url` di playbook `01-dependensi-os.yml` & `02-instalasi-core.yml` tiap stack.

### PostgreSQL (pg-1/2/3) — `postgres/`

**Fase 1 — paket dasar OS (apt, repo Ubuntu 24.04):**

| Paket                          | Keterangan                                    |
|--------------------------------|-----------------------------------------------|
| curl, wget                     | Tools unduh                                   |
| ca-certificates, gnupg         | Trust chain + verifikasi key repo             |
| python3-pip, python3-venv      | Dasar venv Patroni (PEP 668)                  |
| libpq-dev, python3-dev         | Header/kebutuhan build psycopg2               |
| build-essential                | Compiler & build tools                        |

**Fase 2 — paket inti:**

| Paket                  | Sumber                                | Keterangan                          |
|------------------------|---------------------------------------|-------------------------------------|
| postgresql-17          | apt (repo PGDG `noble-pgdg`)          | Server DB                           |
| postgresql-client-17   | apt (repo PGDG)                       | Client `psql`                       |
| etcd + etcdctl 3.5.32  | binary GitHub → `/usr/local/bin`      | DCS / leader lock                   |
| patroni[etcd3]         | pip venv `/opt/patroni-venv`          | HA manager (Python)                 |
| psycopg2-binary        | pip venv `/opt/patroni-venv`          | Driver Python → PostgreSQL          |
| pgbouncer              | apt (repo Ubuntu)                     | Connection pool                     |

> Autostart fase 2: hanya `pgbouncer` (unit dari package apt). etcd & Patroni unit-nya
> node-specific + butuh config file (03a/03b) — enable/start di fase konfigurasi cluster.

### Valkey (vk-1/2/3) — `valkey/`

**Fase 1 — persiapan (tanpa paket build — install binary):**

| Item                 | Keterangan                                   |
|----------------------|----------------------------------------------|
| user & grup `valkey` | System user, shell nologin                   |
| direktori data       | `/var/lib/valkey`, `/var/log/valkey`, `/var/run/valkey`, `/etc/valkey` |

**Fase 2 — paket inti (binary resmi valkey.io 9.1.1 → `/usr/local/bin`):**

| Paket                     | Keterangan                                   |
|---------------------------|----------------------------------------------|
| valkey-server             | Server (primary/replica) — versi 9.1.1       |
| valkey-sentinel           | Sentinel (failover)                          |
| valkey-cli, valkey-benchmark, valkey-check-{rdb,aof} | Utilitas client & tool    |

> Unduh dari `download.valkey.io` (sha256 di-pin di `group_vars/valkey.yml`), ekstrak,
> binary ke `/usr/local/bin`. Unit systemd dari `valkey/files/` (`valkey.service`,
> `valkey-sentinel.service` — hardened, proven di lab). Kedua service di-ENABLE di
> fase 2 (autostart), belum di-start — config cluster = fase 03.

### RabbitMQ (rb-1/2/3) — `rabbitmq/`

**Fase 1 — paket OS (apt, repo Ubuntu 24.04):**

| Paket    | Keterangan                                      |
|----------|-------------------------------------------------|
| ufw      | Firewall (port 22/4369/25672/5672/15672 dibuka) |

**Fase 2 — paket inti:**

| Paket                  | Sumber                                | Keterangan                          |
|------------------------|---------------------------------------|-------------------------------------|
| curl, gnupg, ca-certificates | apt (repo Ubuntu)              | Prasyarat import signing key        |
| rabbitmq-server        | apt (repo Team RabbitMQ, pin `4.2.9-1`) | Server (default_queue_type=quorum) |
| erlang-base, erlang-crypto, erlang-ssl, dll (17 paket inti) | apt (repo Team RabbitMQ Erlang, pin `1:27.3.4.16-1`) | Runtime RabbitMQ (OTP 27.x) |
| rabbitmq_management    | plugin (`rabbitmq-plugins enable`)    | UI & API port 15672                 |

> Signing key Team RabbitMQ (fingerprint `0A9AF2115F4687BD29803A206B73A36E6026DFCA`)
> → dearmor ke `/usr/share/keyrings/com.rabbitmq.team.gpg`, repo di
> `/etc/apt/sources.list.d/rabbitmq-{erlang,server}.list`.
> Repo Cloudsmith TIDAK dipakai — erlang 27.x & rabbitmq-server 4.2.9 tidak tersedia di sana.
> `rabbitmq-server` di-ENABLE di fase 2 (autostart). UFW terpasang tapi TIDAK diaktifkan
> (firewall mati — keputusan scope install-only).

---

## 4. URL Repository & Source

| Komponen  | URL                                                                                                  | Keterangan                     |
|-----------|------------------------------------------------------------------------------------------------------|--------------------------------|
| PGDG      | `http://apt.postgresql.org/pub/repos/apt` (suitename `-pgdg`)                                        | Repo PostgreSQL 17             |
| PGDG key  | `https://www.postgresql.org/media/keys/ACCC4CF8.asc` → dearmor ke `/usr/share/keyrings/pgdg.gpg`     | Signing key PGDG               |
| etcd      | `https://github.com/etcd-io/etcd/releases/download/v3.5.32/etcd-v3.5.32-linux-amd64.tar.gz`          | Binary release GitHub          |
| Patroni   | PyPI via pip: `patroni[etcd3]`, `psycopg2-binary`                                                    | Dalam venv `/opt/patroni-venv` |
| Valkey    | `https://download.valkey.io/releases/valkey-9.1.1-noble-x86_64.tar.gz` | Binary artifact resmi valkey.io (noble x86_64, sha256 di-pin) |
| Erlang    | `https://deb1.rabbitmq.com/rabbitmq-erlang/ubuntu/noble noble main` (mirror: deb2) | Repo Team RabbitMQ (resmi) |
| RabbitMQ  | `https://deb1.rabbitmq.com/rabbitmq-server/ubuntu/noble noble main` (mirror: deb2) | Repo Team RabbitMQ (resmi) |
| Signing key | `https://keys.openpgp.org/vks/v1/by-fingerprint/0A9AF2115F4687BD29803A206B73A36E6026DFCA` | dearmor → `/usr/share/keyrings/com.rabbitmq.team.gpg` |

---

## 5. Port yang Digunakan

### PostgreSQL (pg-1/2/3)
| Port  | Service                  | Keterangan                              |
|-------|--------------------------|-----------------------------------------|
| 5432  | PostgreSQL               | Backend DB                              |
| 8008  | Patroni REST API         | Health-check `/primary`, `/replica`     |
| 2379  | etcd client              | DCS / leader lock                       |
| 2380  | etcd peer                | Komunikasi antar node etcd              |
| 6432  | PgBouncer                | Connection pool (client masuk)          |
| 100   | HAProxy VIP (Phase 5)    | 192.168.1.100 — belum dibangun          |

### Valkey (vk-1/2/3)
| Port  | Service          | Keterangan                              |
|-------|------------------|-----------------------------------------|
| 6379  | valkey-server    | Primary & replica (replikasi)           |
| 26379 | valkey-sentinel  | Monitoring + failover (quorum=2)        |

### RabbitMQ (rb-1/2/3)
| Port  | Service        | Keterangan                              |
|-------|----------------|-----------------------------------------|
| 4369  | EPMD           | Discovery antar node                    |
| 5672  | AMQP           | Koneksi client (producer/consumer)      |
| 15672 | Management     | UI & API management                     |
| 25672 | Erlang cluster | Komunikasi cluster (distribution)       |
| 22    | SSH            | Dibuka di UFW agar tidak putus          |

---

## 6. Path File Penting

### PostgreSQL (pg-1/2/3)
| Path                                   | Fungsi                                   |
|----------------------------------------|------------------------------------------|
| `/etc/patroni/patroni.yml`             | Config Patroni (per node, statis)        |
| `/opt/patroni-venv/bin/patroni`        | Binary Patroni                           |
| `/opt/patroni-venv/bin/patronictl`     | CLI manajemen cluster (`-c /etc/patroni/patroni.yml list`) |
| `/var/lib/postgresql/17/main`          | Data dir PostgreSQL (dibuat Patroni)     |
| `/usr/lib/postgresql/17/bin`           | Bin dir PostgreSQL (psql, pg_dropcluster)|
| `/etc/pgbouncer/pgbouncer.ini`         | Config PgBouncer (statis)                |
| `/etc/pgbouncer/userlist.txt`          | SCRAM secret (ditarik runtime dari pg_authid) |
| `/etc/systemd/system/etcd.service`     | Unit etcd (statis per node)              |
| `/etc/systemd/system/patroni.service`  | Unit Patroni                             |
| `/var/lib/etcd`                        | Data dir etcd                            |
| `/usr/local/bin/etcd`, `etcdctl`       | Binary etcd                              |
| `/var/lib/postgresql/.pgpass`          | Credential verify (dibuat playbook 03c)  |

### Valkey (vk-1/2/3)
| Path                                   | Fungsi                                   |
|----------------------------------------|------------------------------------------|
| `/etc/valkey/valkey.conf`              | Config server (primary vs replica)       |
| `/etc/valkey/sentinel.conf`            | Config sentinel (sama semua node, writable oleh user valkey) |
| `/var/lib/valkey/`                     | Data: `dump.rdb` (RDB) + `appendonly.aof` (AOF) |
| `/var/log/valkey/valkey.log`           | Log valkey-server                        |
| `/var/log/valkey/sentinel.log`         | Log sentinel                             |
| `/usr/local/bin/valkey-server`, `valkey-cli`, `valkey-sentinel` | Binary (dari valkey.io) |
| `/etc/systemd/system/valkey.service`   | Unit valkey-server (dari files/, hardened) |
| `/etc/systemd/system/valkey-sentinel.service` | Unit sentinel (dari files/, hardened) |

### RabbitMQ (rb-1/2/3)
| Path                                   | Fungsi                                   |
|----------------------------------------|------------------------------------------|
| `/etc/rabbitmq/rabbitmq.conf`          | Config (default_queue_type = quorum)     |
| `/var/lib/rabbitmq/.erlang.cookie`     | Erlang cookie (wajib identik antar node, mode 0400) |
| `/var/log/rabbitmq/`                   | Log RabbitMQ                             |
| `/etc/systemd/system/rabbitmq-server.service.d/limits.conf` | Drop-in LimitNOFILE=65536 |
| `/usr/lib/rabbitmq/bin/rabbitmqctl`    | CLI (cluster_status, join_cluster, dll)  |

### Ansible (controller)
| Path                                   | Fungsi                                   |
|----------------------------------------|------------------------------------------|
| `/root/ansible-automation/bkpm-ha-v2/` | Playbook v2 (model 3 fase, tanpa jinja)  |
| `/root/ansible-automation/bkpm-ha-v2/inventory.ini` | Inventory v2 (self-contained) |
| `/root/ansible-automation/bkpm-ha-v2/group_vars/` | Variabel per project          |
| `/root/ansible-automation/`            | Playbook lama (referensi, tidak disentuh)|

---

## 7. Urutan Eksekusi Playbook (v2)

```
# PostgreSQL (wajib urut)
01-dependensi-os → 02-instalasi-core → 03a-etcd → 03b-patroni → 03c-pgbouncer

# Valkey (wajib urut)
01-dependensi-os → 02-instalasi-core → 03-konfigurasi

# RabbitMQ (wajib urut)
01-dependensi-os → 02-instalasi-core → 03-konfigurasi
```

Verifikasi tiap fase:

| Fase          | Verifikasi                                                                                                 |
|---------------|------------------------------------------------------------------------------------------------------------|
| 02 (install)  | Paket apt (`dpkg-query`: postgresql-17, pgbouncer, rabbitmq-server, erlang) + `apt-cache madison` (rabbitmq-server, erlang) + binary versi (`etcd --version`, `psql --version`, `patroni --version`, `valkey-server --version`, `rabbitmqctl version`) + autostart (`systemctl is-enabled` pgbouncer, valkey-server, valkey-sentinel, rabbitmq-server) |
| 03 (config)   | Cluster jalan: `patronictl list` (1 Leader), `valkey-cli -p 26379 sentinel get-master-addr-by-name mymaster`, `rabbitmqctl cluster_status` |

---

*Dibuat: 2026-08-27 · bersumber dari bkpm-ha-v2 (playbook aktif) — playbook lama di `/root/ansible-automation/` tetap referensi.*
