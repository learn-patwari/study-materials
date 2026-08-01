# Convert an Android Tablet into a Linux Server

A practical guide to repurposing an Android tablet as a lightweight, always-on Linux server — great for home automation, a personal cloud, a dev sandbox, or a learning lab.

---

## Table of Contents

1. [Why This Works](#why-this-works)
2. [Choose Your Approach](#choose-your-approach)
3. [Method 1 — Termux (No Root)](#method-1--termux-no-root)
4. [Method 2 — UserLAnd (No Root, Full Distro)](#method-2--userland-no-root-full-distro)
5. [Method 3 — Linux Deploy (Root Required)](#method-3--linux-deploy-root-required)
6. [Set Up Core Server Services](#set-up-core-server-services)
7. [Keep It Always-On](#keep-it-always-on)
8. [Access Remotely via SSH](#access-remotely-via-ssh)
9. [Optional: Expose to the Internet](#optional-expose-to-the-internet)
10. [Troubleshooting](#troubleshooting)
11. [Comparison Table](#comparison-table)

---

## Why This Works

Android runs on the Linux kernel. The Android userspace sits on top of it, but you can install a parallel Linux environment in the same kernel without replacing Android. The tablet becomes a low-power ARM server you can SSH into from any machine on your network.

**Typical specs of a repurposed tablet:**

| Resource | Typical value |
|----------|--------------|
| CPU | 4–8 core ARM (1.5–2.4 GHz) |
| RAM | 2–8 GB |
| Storage | 32–256 GB |
| Power draw | 5–15 W (vs. 60–90 W for a NUC) |
| Cost | $0 (use what you have) |

---

## Choose Your Approach

| | Root needed | Full Linux distro | Difficulty |
|---|---|---|---|
| **Termux** | No | Partial (packages only) | Easy |
| **UserLAnd** | No | Yes (chroot) | Easy–Medium |
| **Linux Deploy** | Yes | Yes (chroot/image) | Medium |

**Recommendation:** Start with **Termux** for most use-cases. Move to **Linux Deploy** only if you need full systemd or kernel-level access.

---

## Method 1 — Termux (No Root)

Termux gives you a real bash shell, `apt`/`pkg` package manager, and the ability to run servers (SSH, HTTP, databases) without any root or ROM modification.

### 1.1 Install Termux

> **Important:** Do NOT install Termux from the Google Play Store — that version is abandoned and outdated.  
> Install from [F-Droid](https://f-droid.org/en/packages/com.termux/) or from the [Termux GitHub releases](https://github.com/termux/termux-app/releases).

```bash
# After opening Termux, update the package index
pkg update && pkg upgrade -y
```

### 1.2 Install a Linux-like environment (proot-distro)

`proot-distro` lets you run a full Ubuntu/Debian/Alpine chroot inside Termux without root.

```bash
# Install proot-distro
pkg install proot-distro -y

# List available distros
proot-distro list

# Install Ubuntu (LTS)
proot-distro install ubuntu

# Enter Ubuntu shell
proot-distro login ubuntu
```

Inside Ubuntu you can now run:

```bash
apt update && apt upgrade -y
apt install -y openssh-server nginx python3 nodejs git
```

### 1.3 Enable SSH in Termux (direct, without proot)

If you just want SSH access to the Termux shell itself:

```bash
pkg install openssh -y

# Set a password (used for SSH auth)
passwd

# Start sshd (listens on port 8022 by default — not 22, because <1024 needs root)
sshd

# From another machine on the same Wi-Fi:
# ssh -p 8022 <your-tablet-ip>
```

Find your tablet's IP:

```bash
pkg install iproute2 -y
ip addr show wlan0 | grep "inet "
```

---

## Method 2 — UserLAnd (No Root, Full Distro)

UserLAnd is a GUI app that installs Debian/Ubuntu/Alpine in a proot chroot with a one-tap setup. Best for people who want a point-and-click install.

### 2.1 Install UserLAnd

Install from the [Google Play Store](https://play.google.com/store/apps/details?id=tech.ula) or [F-Droid](https://f-droid.org/en/packages/tech.ula/).

### 2.2 Set Up a Distro

1. Open UserLAnd → tap **+** to create a new session.
2. Choose **Ubuntu** or **Debian**.
3. Choose **SSH** as the connection type (not VNC).
4. Set a username and password.
5. UserLAnd downloads and configures the rootfs automatically.

### 2.3 Connect via SSH

UserLAnd's SSH server listens on **port 2022** by default.

```bash
# From another machine
ssh -p 2022 <username>@<tablet-ip>
```

Or use the built-in terminal inside the UserLAnd app.

---

## Method 3 — Linux Deploy (Root Required)

Linux Deploy installs a full Debian/Ubuntu/Arch/Fedora image into a loop-mounted disk image. It starts at boot and runs in a proper chroot. This is the closest to a real server experience.

### 3.1 Prerequisites

- Rooted Android device
- [BusyBox](https://play.google.com/store/apps/details?id=stericson.busybox) installed
- [Linux Deploy](https://play.google.com/store/apps/details?id=ru.meefik.linuxdeploy) installed

### 3.2 Configure the Image

1. Open Linux Deploy → tap **Properties** (wrench icon).
2. **Distribution:** Ubuntu 22.04 (Jammy)
3. **Architecture:** `arm64` (for most modern tablets) or `armhf`
4. **Installation path:** `/sdcard/linux.img` (or a path with enough space)
5. **Image size:** at least 4096 MB (4 GB)
6. **Username / Password:** set your login credentials
7. **SSH:** enable and set port (e.g., 22 or 2222)

### 3.3 Install and Start

```
Tap  ▶  (Install)  →  Wait ~10 min for download/extraction
Tap  ▶  (Start)    →  Linux container boots
```

### 3.4 SSH In

```bash
ssh -p 22 <username>@<tablet-ip>
# or port 2222 if you set that
```

Inside, it's a full Debian/Ubuntu with `apt`, `systemctl`, cron — everything.

---

## Set Up Core Server Services

These steps work in any of the three methods once you have a shell.

### Web Server — Nginx

```bash
apt install -y nginx
# For Termux without proot:
pkg install nginx -y

# Start nginx
nginx
# or, if systemd is available:
systemctl enable --now nginx
```

Default web root: `/var/www/html` (Debian/Ubuntu) or `$PREFIX/share/nginx/html` (Termux).

### Database — SQLite / MariaDB

```bash
# SQLite (lightweight, no daemon)
apt install -y sqlite3

# MariaDB (MySQL-compatible)
apt install -y mariadb-server
mysql_secure_installation
systemctl enable --now mariadb
```

### Node.js / Python server

```bash
# Node.js
apt install -y nodejs npm
# or: pkg install nodejs -y (Termux)

# Python HTTP server (quick test)
python3 -m http.server 8080
```

### Samba (Windows file sharing)

```bash
apt install -y samba
# Edit /etc/samba/smb.conf, then:
systemctl enable --now smbd nmbd
```

### Docker (Linux Deploy / rooted only)

Docker requires real Linux kernel features that proot does not fully expose. It works reliably only with **Linux Deploy** on a rooted device that supports the required kernel modules (`cgroups v2`, `overlayfs`).

```bash
curl -fsSL https://get.docker.com | sh
systemctl enable --now docker
```

---

## Keep It Always-On

Android aggressively kills background processes to save battery. You must defeat this to keep your server running.

### Battery optimization

Go to **Settings → Battery → Battery optimization** and set your terminal app (Termux / UserLAnd) to **"Not optimized"** (or "Unrestricted").

### Prevent screen sleep (Termux)

```bash
# Acquire a wake lock so the CPU doesn't throttle
termux-wake-lock
```

Install the **Termux:API** add-on app (from F-Droid) first.

### Keep Wi-Fi on during sleep

**Settings → Wi-Fi → Advanced → Keep Wi-Fi on during sleep → Always**

### Screen-off mode

You don't need the screen on. The server keeps running with the screen off as long as you've set battery optimization to unrestricted.

### Auto-start on reboot (Termux)

Create `~/.termux/boot/start-server.sh` and install the **Termux:Boot** add-on:

```bash
mkdir -p ~/.termux/boot
cat > ~/.termux/boot/start-server.sh << 'EOF'
#!/data/data/com.termux/files/usr/bin/bash
termux-wake-lock
sshd
# Add other services here:
# cd ~/myapp && node server.js &
EOF
chmod +x ~/.termux/boot/start-server.sh
```

Install [Termux:Boot](https://f-droid.org/en/packages/com.termux.boot/) from F-Droid. This script runs automatically when the tablet reboots.

---

## Access Remotely via SSH

### From Linux / macOS

```bash
ssh -p 8022 <tablet-ip>          # Termux default port
ssh -p 2022 <username>@<tablet-ip>  # UserLAnd default port
ssh <username>@<tablet-ip>          # Linux Deploy (port 22)
```

### From Windows

Use [PuTTY](https://www.putty.org/) or Windows Terminal with the built-in SSH client:

```powershell
ssh -p 8022 <tablet-ip>
```

### Set up SSH key authentication (recommended)

On your laptop:

```bash
# Generate key if you don't have one
ssh-keygen -t ed25519 -C "my-laptop"

# Copy the public key to the tablet
ssh-copy-id -p 8022 <tablet-ip>
# or manually:
cat ~/.ssh/id_ed25519.pub | ssh -p 8022 <tablet-ip> "mkdir -p ~/.ssh && cat >> ~/.ssh/authorized_keys"
```

Now you can SSH without a password.

---

## Optional: Expose to the Internet

If you want to reach your server from outside your home network, you have two safe options — avoid port-forwarding your router directly unless you know what you're doing.

### Option A — Cloudflare Tunnel (recommended, free)

```bash
# Install cloudflared
wget -O cloudflared https://github.com/cloudflare/cloudflared/releases/latest/download/cloudflared-linux-arm64
chmod +x cloudflared

# Authenticate once
./cloudflared tunnel login

# Create a tunnel and route
./cloudflared tunnel create my-tablet
./cloudflared tunnel route dns my-tablet server.yourdomain.com

# Run the tunnel (point to your local service)
./cloudflared tunnel run --url http://localhost:80 my-tablet
```

### Option B — Tailscale VPN (easiest)

```bash
curl -fsSL https://tailscale.com/install.sh | sh
tailscale up
```

Your tablet gets a stable `100.x.x.x` IP reachable from all your Tailscale devices — no port forwarding, no firewall rules.

---

## Troubleshooting

| Problem | Fix |
|---------|-----|
| SSH connection refused | Check that `sshd` is running: `ps aux \| grep sshd`. Restart with `sshd` or `pkill sshd && sshd` |
| Server dies after screen off | Set battery optimization to "Not optimized"; run `termux-wake-lock` |
| Server dies after reboot | Install Termux:Boot and add your startup script |
| `proot-distro login` hangs | Reboot Termux; check available storage (`df -h`) |
| Port 22 permission denied | Ports below 1024 require root. Use 8022, 2022, etc., or use Linux Deploy with root |
| `apt update` fails (Termux) | Run `pkg update` instead; Termux uses its own package manager, not `apt` directly |
| High battery drain | Disable Wi-Fi scanning, Bluetooth, and GPS. Plug the tablet in for 24/7 use |

---

## Comparison Table

| Feature | Termux | UserLAnd | Linux Deploy |
|---------|--------|----------|-------------|
| Root required | No | No | Yes |
| Full Linux distro | Partial | Yes | Yes |
| `systemd` support | No | No | Limited |
| Docker support | No | No | Yes (kernel-dependent) |
| Auto-start on boot | Via Termux:Boot | No (manual) | Yes |
| Stability | High | Medium | High |
| Best for | SSH shell, dev tools, lightweight servers | Learning Linux, small services | Full server replacement |
| Setup difficulty | Easy | Easy | Medium |

---

## Next Steps

- **Home automation:** install [Home Assistant](https://www.home-assistant.io/) (Python-based, runs well in proot)
- **Personal cloud:** install [Nextcloud](https://nextcloud.com/) with Nginx + MariaDB
- **Code server:** install `code-server` for a browser-based VS Code
- **Pi-hole DNS:** install [Pi-hole](https://pi-hole.net/) to block ads network-wide
- **Monitor resources:** `htop`, `glances`, or `neofetch` to see CPU/RAM usage
