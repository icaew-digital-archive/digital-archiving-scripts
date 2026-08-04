# Browsertrix Cloud Setup — Instructions

| | |
|---|---|
| **Domain** | browsertrix.craiglmccarthy.com |
| **Droplet** | DigitalOcean, region LON1 (London), Ubuntu 24.04 LTS |
| **Plan** | s-4vcpu-8gb (4 vCPU / 8GB RAM / 160GB disk) |
| **IP** | XX.XX.XX.XX |

## What you need before starting

- A registered domain name, with access to its DNS settings (either at your registrar directly, or wherever its nameservers point).
- A DigitalOcean account with billing set up (or any cloud provider — this guide uses DO, see **Step 0** below).
- An SSH key pair on your own computer. If you don't already have one:

  ```bash
  ssh-keygen -t ed25519
  ```

  (Accept the default file location, a passphrase is optional.) This creates `~/.ssh/id_ed25519` (private, keep secret) and `~/.ssh/id_ed25519.pub` (public, safe to share/upload).

This guide goes in order: **Step 0** (create the server + point your domain at it) → **Step 1** (prove DNS/networking actually works) → **Step 2/3** (install Kubernetes) → **Step 4** (install Browsertrix itself).

---

## Step 0 — Create the droplet and point your domain at it

### 0a) Create the droplet

At <https://cloud.digitalocean.com/droplets/new>:

- **Region:** pick one close to you/your users (used LON1 - London)
- **Image / OS:** Ubuntu 24.04 (LTS) x64
- **Droplet Plan:** Basic → Regular (SSD) → whichever size fits your budget (used `s-4vcpu-8gb`: 4 vCPU / 8GB RAM / 160GB disk, ~$48/mo)
- **Authentication:** SSH Keys → add/select the public key from "What you need before starting" above (paste the contents of `id_ed25519.pub`, or upload it). **Do NOT use password auth only.**
- **Backups:** optional, adds cost (~$9.60-14.40/mo) — skip if going for the cheapest/simplest setup
- Give it a name, pick a project, click **Create Droplet**
- Once created, note its public IPv4 address from the droplet list (this guide's example: `XX.XX.XX.XX`)

### 0b) Point your domain at that IP

Go to wherever you manage DNS for your domain (your registrar, or DigitalOcean's own DNS if you delegated nameservers there) and add an **A record**:

| Field | Value |
|---|---|
| Type | A |
| Name | the subdomain you want, e.g. `browsertrix` (this guide uses browsertrix.craiglmccarthy.com) |
| Value | the droplet's public IPv4 from step 0a |
| TTL | default is fine |

DNS changes can take anywhere from a minute to a few hours to propagate depending on your registrar/TTL. Check it's resolving with:

```bash
dig +short browsertrix.craiglmccarthy.com
```

(Replace with your own domain.) It should print the droplet's IP. **Don't move on to Step 1 until this shows the right IP.**

### 0c) Confirm you can SSH in as root

```bash
ssh root@<your-droplet-ip>
```

If this hangs or is refused, double-check the correct SSH key was attached when the droplet was created (0a).

> **All commands from here on are meant to be run in an SSH session on the droplet** unless stated otherwise.
>
> ```bash
> ssh root@XX.XX.XX.XX
> ```

---

## Step 1 — Verify DNS points at this server

> _(Done, kept for reference. Status: confirmed working 2026-07-28.)_

Run this on the droplet to serve a basic test page on port 80:

```bash
mkdir -p /tmp/dns-check && echo "<h1>It works! Served from $(hostname)</h1>" > /tmp/dns-check/index.html && python3 -m http.server 80 --directory /tmp/dns-check
```

Then, from a browser or another machine, visit:

```
http://browsertrix.craiglmccarthy.com/
```

You should see "It works! Served from ubuntu-s-4vcpu-8gb-lon1".

Test with **more than one method**, since browsers may auto-upgrade to `https://` (which will show nothing/an error since there's no TLS cert yet) and give a false impression that it's broken:

- Try at least two different browsers, explicitly typing the `http://` prefix in the address bar.
- Also test from the command line:

  ```bash
  curl -i http://browsertrix.craiglmccarthy.com/
  wget -qO- http://browsertrix.craiglmccarthy.com/
  ```

When done, press **Ctrl+C** to stop the server, then clean up:

```bash
rm -rf /tmp/dns-check
```

---

## Step 2 — Install MicroK8s

```bash
sudo snap install microk8s --classic
sudo usermod -a -G microk8s $USER
mkdir -p ~/.kube
sudo chown -f -R $USER ~/.kube
newgrp microk8s
```

---

## Step 3 — Enable required addons

_(dns, storage, ingress, TLS via cert-manager)_

```bash
microk8s enable dns storage ingress cert-manager
```

Then confirm everything is up:

```bash
microk8s status --wait-ready
microk8s kubectl get pods -A
```

---

## Step 4 — Install Helm + deploy Browsertrix

> **Status (2026-07-28):** Step 2/3 confirmed healthy — cert-manager, ingress (Traefik), coredns, calico, hostpath-provisioner all Running. MicroK8s already ships Helm (no separate install needed) — use `microk8s helm3`.

> **Note:** MicroK8s's ingress addon uses Traefik with ingress class name `public` (**NOT** nginx, which is the chart's default). The official `chart/examples/microk8s-hosted.yaml` example handles this correctly, so we use that as the base config rather than hand-writing `values.yaml`.

### 4a) Clone the chart repo, pinned to the latest stable release (v1.24.0)

```bash
git clone --branch v1.24.0 --depth 1 https://github.com/webrecorder/browsertrix.git
cd browsertrix
```

### 4b/4c) Write `./chart/my-config.yaml` directly

No manual editing needed — paste this whole block as one command, it writes the file for you. **Replace `<YOUR_SUPERUSER_PASSWORD>` with your own strong password before running.**

```bash
cat > ./chart/my-config.yaml << 'EOF'
ingress:
  host: "browsertrix.craiglmccarthy.com"
  cert_email: "craig.mccarthy@icaew.com"
  scheme: "https"
  tls: true
  annotations:
    cert-manager.io/cluster-issuer: "cert-main"

ingress_class: "public"

signer:
  enabled: false

superuser:
  email: "craig.mccarthy@icaew.com"
  password: "<YOUR_SUPERUSER_PASSWORD>"   # replace with your own strong password before running
EOF
```

> **Note (added after first deploy attempt):** the chart's `ingress.yaml` template only adds the `cert-manager.io/cluster-issuer` annotation automatically when `ingress_class == "nginx"`. Since MicroK8s uses `ingress_class "public"` (Traefik), that annotation never gets added on its own, so cert-manager is never told to issue a cert — this is why `kubectl get certificate -A` showed "No resources found" and only `http://` worked. The explicit `ingress.annotations` block above works around this by adding the annotation manually (the template supports arbitrary user annotations regardless of `ingress_class`).
>
> This is a trimmed-down equivalent of `chart/examples/microk8s-hosted.yaml` with the placeholders already filled in and signing left disabled.

### 4d) Deploy

```bash
microk8s helm3 upgrade --install -f ./chart/values.yaml -f ./chart/my-config.yaml btrix ./chart/
```

### 4e) Watch pods come up

(Can take a few minutes, esp. first-time image pulls.)

```bash
microk8s kubectl get pods -A -w
```

Press **Ctrl+C** once everything shows `Running`/`Completed`.

### 4f) Check the TLS certificate was issued

(Needs DNS + port 80 reachable — already confirmed working in Step 1.)

```bash
microk8s kubectl get certificate -A
# if stuck "False" for a while:
microk8s kubectl describe certificate -n default <name>
```

> **Status (2026-07-28):** first attempt showed "No resources found" here — see the note above 4d. Fix applied: re-ran the `my-config.yaml` heredoc (now includes `ingress.annotations.cert-manager.io/cluster-issuer`), then re-ran 4d (`helm upgrade --install` is safe/idempotent to re-run), then re-checked this command — should now show a `cert-main` Certificate, `READY=False` at first, flipping to `True` within a minute or two as the HTTP-01 challenge completes.

### 4g) Once ready, visit

```
https://browsertrix.craiglmccarthy.com
```

and log in with the superuser email/password set above.

---

## How many crawls / browser windows can this droplet run?

Sizing for this box: `s-4vcpu-8gb` (4 vCPU / 8GB RAM).

**Resource cost per crawl** (from the chart defaults, `chart/values.yaml`):

- First browser window in a crawl: **900m CPU + 1024Mi (1GB) RAM**
- Each **additional** window in same crawl: **+600m CPU + +768Mi RAM**

So a crawl at the default 2 windows = **1.5 vCPU / 1.75GB RAM**.

**Fixed overhead** already running (Browsertrix backend/frontend/mongo/redis/minio + MicroK8s system pods) eats roughly **0.5-1 vCPU and 2.5-3GB RAM**, leaving about **~3-3.5 vCPU and ~5GB RAM** free for actual crawling.

**Practical guidance:**

- **~4 total browser windows** is a safe, comfortable number (e.g. 2 concurrent crawls × 2 windows).
- The real ceiling is **~5-6 total windows**, and you get MORE of them by running **fewer, larger crawls** rather than many small concurrent ones, because each separate crawl pays the fixed 900m/1GB "base" cost again.

  | Configuration | Cost | Verdict |
  |---|---|---|
  | One crawl, 5 windows | 3.3 vCPU / 4GB | fits comfortably |
  | One crawl, 6 windows | 3.9 vCPU / 4.75GB | tight on CPU |
  | 3 crawls × 2 windows | 4.5 vCPU / 5.25GB | over budget |

- Memory is the harder ceiling than CPU (see below) — **size around RAM**.

## What happens if you go over budget

CPU and memory fail differently, because of how the crawler pods are configured (crawler pods get a CPU *request* but no CPU *limit*, and a real *memory limit* set equal to their memory request):

- **Too much concurrency** (not enough CPU to schedule a new pod): Kubernetes simply won't start the new crawl pod — it sits in `Pending` until capacity frees up. Nothing crashes; running crawls keep going, the new one just waits.
- **Too many windows crammed into one crawl** (pod exceeds its memory limit): the Linux OOM killer kills that container. Crawler pods use `restartPolicy: OnFailure`, so it auto-restarts and resumes from its last checkpoint (crawl state lives in Redis) — but you'll see restart counts climb and the crawl stall/slow while it recovers. **This is the more disruptive failure mode, which is why you size around memory.**

**How to spot each symptom:**

```bash
microk8s kubectl get pods -A          # look for STATUS "Pending" or high RESTARTS
microk8s kubectl describe pod <name>  # events show "Insufficient cpu" (pending) or "OOMKilled" (memory)
```

**Optional** — see live resource usage to tune the numbers for real:

```bash
microk8s enable metrics-server
microk8s kubectl top pods -A
```

---

## Notes / decisions so far

- **Chose DigitalOcean over AWS:** no EKS control-plane fee, official Ansible playbook exists for DO, cheaper for this scale.
- **Chose MicroK8s over k3s:** fewer manual steps (k3s needs Traefik disabled and nginx-ingress + cert-manager installed separately by hand).
- **Backups add-on** ($9.60-14.40/mo extra) was optional, not required to proceed.
- **WACZ signing / second domain deliberately skipped** — user wants the simplest possible deployment. `signer.enabled` left false, `mongo_auth` left at chart defaults (Mongo isn't exposed outside the cluster).
- **Pinned chart install to release v1.24.0** (latest stable as of 2026-07-28) rather than tracking main branch.
- **MicroK8s's ingress addon = Traefik with ingress class `public`**, not nginx (the chart's default) — this is why we use the official `chart/examples/microk8s-hosted.yaml` as the base config.

---

## Teardown — deleting everything

Deleting the droplet removes MicroK8s and Browsertrix in one step; there's nothing separate to uninstall first.

> **Before you destroy anything:** crawl data (WACZ files, collections) lives in MinIO on the droplet's own disk via the `storage` addon (Step 3) — it is **not** backed up anywhere else. Export or download anything you need to keep (via the Browsertrix UI, or `microk8s kubectl cp` off the MinIO pod) before proceeding. Once the droplet is destroyed, that data is gone.

### 1) Delete the droplet

At <https://cloud.digitalocean.com/droplets>:

- Select the droplet (`ubuntu-s-4vcpu-8gb-lon1`, or whatever you named it in Step 0a)
- **Destroy** → **Destroy Droplet** → confirm

This stops billing for the droplet immediately. Any snapshots/backups you opted into (Step 0a) are billed separately and must be deleted on their own if you don't want them kept.

### 2) Remove the DNS record

Go back to wherever you added the A record in Step 0b and delete it (or repoint it elsewhere). Otherwise `browsertrix.craiglmccarthy.com` (or your subdomain) will keep resolving to an IP that no longer belongs to you — DigitalOcean recycles released IPs to other customers.

### 3) Double-check nothing's still running

```bash
doctl compute droplet list   # requires doctl CLI + auth; alternatively just check the DO dashboard
```

Confirms the droplet no longer appears in your account.
