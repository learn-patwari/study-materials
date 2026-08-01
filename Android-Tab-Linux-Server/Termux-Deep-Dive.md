# Termux: Android Tablet → Linux Server (Deep Dive)

Everything you need to turn an Android tablet into a real server using Termux — no root required.

---

## Table of Contents

1. [Install Termux the Right Way](#1-install-termux-the-right-way)
2. [First Boot — Essential Setup](#2-first-boot--essential-setup)
3. [Package Management](#3-package-management)
4. [SSH Server — Access From Any Machine](#4-ssh-server--access-from-any-machine)
5. [Run a Full Ubuntu/Debian Inside Termux (proot-distro)](#5-run-a-full-ubuntudebian-inside-termux-proot-distro)
6. [File System Layout](#6-file-system-layout)
7. [Storage — Access Your Android Files](#7-storage--access-your-android-files)
8. [Server Services](#8-server-services)
9. [Keep the Server Alive 24/7](#9-keep-the-server-alive-247)
10. [Auto-Start on Reboot (Termux:Boot)](#10-auto-start-on-reboot-termuxboot)
11. [Termux:API — Tap Into Android Hardware](#11-termuxapi--tap-into-android-hardware)
12. [Networking Cheatsheet](#12-networking-cheatsheet)
13. [Useful Tools & Aliases](#13-useful-tools--aliases)
14. [Limitations](#14-limitations)

---

## 1. Install Termux the Right Way

The Google Play version is unmaintained (frozen at 2020). Always use **F-Droid**.

### Steps

1. Install the F-Droid app store: [f-droid.org](https://f-droid.org)
2. In F-Droid, search **Termux** and install it.
3. Also install these add-on apps (same F-Droid source — do not mix Play + F-Droid versions):
   - **Termux:Boot** — run scripts on device boot
   - **Termux:API** — access camera, GPS, sensors, notifications, wake lock

> All four apps (Termux, :Boot, :API, :Widget) must come from the **same source** (all F-Droid or all Play). Mixing sources causes crashes.

---

## 2. First Boot — Essential Setup

```bash
# Update package lists and upgrade everything
pkg update && pkg upgrade -y

# Essential tools
pkg install -y curl wget git nano vim openssh

# Optional but recommended
pkg install -y htop tree iproute2 net-tools dnsutils
```

### Set your timezone

```bash
pkg install -y tzdata
# Termux reads TZ from the env variable
echo 'export TZ="Asia/Kolkata"' >> ~/.bashrc   # change to your timezone
source ~/.bashrc
```

### Set a better shell (optional)

```bash
pkg install -y zsh
chsh -s zsh              # set zsh as default
# Install oh-my-zsh (optional)
sh -c "$(curl -fsSL https://raw.githubusercontent.com/ohmyzsh/ohmyzsh/master/tools/install.sh)"
```

---

## 3. Package Management

Termux uses `pkg` (a wrapper around `apt`). Always use `pkg`, not raw `apt`, in the Termux base environment.

```bash
pkg search <name>        # search for a package
pkg install <name>       # install
pkg uninstall <name>     # remove
pkg list-installed       # show installed packages
pkg upgrade              # upgrade all packages
```

### Useful packages

| Purpose | Package |
|---------|---------|
| Web server | `nginx` |
| Database | `mariadb`, `sqlite`, `redis` |
| Languages | `python`, `nodejs`, `ruby`, `php`, `go`, `rust` |
| Dev tools | `git`, `make`, `clang`, `cmake` |
| Network | `nmap`, `curl`, `wget`, `openssh`, `netcat-openbsd` |
| Editors | `vim`, `nano`, `micro` |
| System | `htop`, `tmux`, `screen`, `cron` |
| Containers | `proot-distro` (chroot, not Docker) |

---

## 4. SSH Server — Access From Any Machine

### Start sshd

```bash
# Generate host keys (only needed once)
ssh-keygen -A

# Set a password for your Termux user
passwd

# Start SSH server
# Termux sshd listens on port 8022 (port 22 needs root)
sshd
```

### Find your tablet's IP

```bash
ip addr show wlan0 | grep "inet "
# or
ifconfig wlan0 | grep "inet "
```

Output example: `inet 192.168.1.105/24` → your IP is `192.168.1.105`

### Connect from another machine

```bash
# Linux / macOS
ssh -p 8022 192.168.1.105

# Windows (PowerShell or CMD)
ssh -p 8022 192.168.1.105
```

### Set up key-based authentication (skip passwords)

On your laptop:

```bash
# Generate a key pair if you don't have one
ssh-keygen -t ed25519

# Copy the public key to the tablet
ssh-copy-id -p 8022 192.168.1.105
```

Or manually:

```bash
# On the tablet in Termux
mkdir -p ~/.ssh
chmod 700 ~/.ssh

# Paste your laptop's ~/.ssh/id_ed25519.pub into this file:
nano ~/.ssh/authorized_keys
chmod 600 ~/.ssh/authorized_keys
```

### sshd config (optional tuning)

```bash
# Termux sshd config lives at:
nano $PREFIX/etc/ssh/sshd_config

# Useful settings:
Port 8022
PasswordAuthentication no      # disable after setting up keys
PubkeyAuthentication yes
PrintMotD yes
```

Restart after changes: `pkill sshd && sshd`

---

## 5. Run a Full Ubuntu/Debian Inside Termux (proot-distro)

Termux's native packages are real Linux binaries but they live in a non-standard prefix (`/data/data/com.termux/files/usr`). If you need a standard Debian/Ubuntu root filesystem — for `apt`, standard paths like `/etc`, `/var`, etc. — use `proot-distro`.

### Install and set up Ubuntu

```bash
pkg install -y proot-distro

# List available distros
proot-distro list
# ubuntu, debian, alpine, fedora, archlinux, void, opensuse, kali, ...

# Install Ubuntu 22.04 (Jammy)
proot-distro install ubuntu

# Enter the Ubuntu shell
proot-distro login ubuntu
```

### Inside Ubuntu (proot)

```bash
# You are now root inside the chroot
apt update && apt upgrade -y

# Install anything you'd install on a real Ubuntu server
apt install -y openssh-server nginx mariadb-server python3 nodejs npm git build-essential

# Create a non-root user
useradd -m -s /bin/bash akshay
echo "akshay:yourpassword" | chpasswd
usermod -aG sudo akshay
```

### SSH into the proot Ubuntu directly

Inside proot Ubuntu, start sshd and point it to a high port:

```bash
# Inside proot ubuntu shell
sed -i 's/#Port 22/Port 2222/' /etc/ssh/sshd_config
service ssh start   # or: /usr/sbin/sshd
```

Then from your laptop:

```bash
ssh -p 2222 akshay@192.168.1.105
```

### Exit and re-enter proot

```bash
exit                          # leave proot, back to Termux
proot-distro login ubuntu     # re-enter
proot-distro login ubuntu -- bash --login   # force login shell
```

### Multiple distros

```bash
proot-distro install debian
proot-distro install alpine
proot-distro login debian     # independent from ubuntu
```

---

## 6. File System Layout

Understanding where things live in Termux:

```
$HOME       = /data/data/com.termux/files/home     (~)
$PREFIX     = /data/data/com.termux/files/usr
  $PREFIX/bin      — executables (bash, ssh, nginx, ...)
  $PREFIX/etc      — config files (sshd_config, nginx.conf, ...)
  $PREFIX/var      — runtime data, logs, PID files
  $PREFIX/share    — shared data, web roots

# proot-distro Ubuntu root:
~/.local/share/proot-distro/installed-rootfs/ubuntu/
```

---

## 7. Storage — Access Your Android Files

By default Termux cannot read your Android `/sdcard`. Run this once to grant access:

```bash
termux-setup-storage
```

This creates symlinks in `~/storage/`:

```
~/storage/shared        → /sdcard              (all files)
~/storage/downloads     → /sdcard/Download
~/storage/dcim          → /sdcard/DCIM
~/storage/pictures      → /sdcard/Pictures
~/storage/music         → /sdcard/Music
~/storage/movies        → /sdcard/Movies
```

Now you can serve files from your Downloads folder, for example:

```bash
cd ~/storage/downloads
python3 -m http.server 8080
# Accessible at http://192.168.1.105:8080
```

---

## 8. Server Services

### Nginx web server

```bash
pkg install -y nginx

# Default web root
ls $PREFIX/share/nginx/html

# Start nginx
nginx

# Stop nginx
nginx -s stop

# Reload config (no downtime)
nginx -s reload

# Config file
nano $PREFIX/etc/nginx/nginx.conf
```

#### Serve a custom directory

```bash
nano $PREFIX/etc/nginx/nginx.conf
```

Add inside the `server {}` block:

```nginx
server {
    listen 8080;
    root /data/data/com.termux/files/home/mysite;
    index index.html;
    location / {
        try_files $uri $uri/ =404;
    }
}
```

### Python HTTP server (instant, no config)

```bash
# Serve current directory on port 8080
python3 -m http.server 8080

# Serve a specific directory
python3 -m http.server 8080 --directory ~/storage/shared
```

### Node.js server

```bash
pkg install -y nodejs

# Quick HTTP server via npx
npx serve ~/myapp -p 3000

# Or a custom Express app
mkdir ~/nodeapp && cd ~/nodeapp
npm init -y
npm install express
cat > index.js << 'EOF'
const express = require('express');
const app = express();
app.get('/', (req, res) => res.send('Hello from Android!'));
app.listen(3000, () => console.log('Running on :3000'));
EOF
node index.js
```

### MariaDB (MySQL-compatible)

```bash
pkg install -y mariadb

# Initialize the data directory (first time only)
mysql_install_db

# Start MariaDB
mysqld_safe &

# Secure installation
mysql_secure_installation

# Connect
mysql -u root -p

# Create a database and user
CREATE DATABASE mydb;
CREATE USER 'myuser'@'localhost' IDENTIFIED BY 'password';
GRANT ALL ON mydb.* TO 'myuser'@'localhost';
FLUSH PRIVILEGES;
```

### Redis

```bash
pkg install -y redis

# Start
redis-server &

# Test
redis-cli ping     # → PONG
```

### SQLite (no daemon, great for simple apps)

```bash
pkg install -y sqlite

sqlite3 ~/mydb.sqlite
# Inside sqlite3:
CREATE TABLE users (id INTEGER PRIMARY KEY, name TEXT);
INSERT INTO users(name) VALUES ('Akshay');
SELECT * FROM users;
.quit
```

### PHP + Nginx

```bash
pkg install -y php-fpm nginx

# Start PHP-FPM
php-fpm

# Configure Nginx to use PHP — edit $PREFIX/etc/nginx/nginx.conf:
# location ~ \.php$ {
#     fastcgi_pass 127.0.0.1:9000;
#     include fastcgi_params;
#     fastcgi_param SCRIPT_FILENAME $document_root$fastcgi_script_name;
# }
```

---

## 9. Keep the Server Alive 24/7

Android's battery manager kills background apps. Three things to fix:

### Step 1 — Battery optimization

Go to **Settings → Apps → Termux → Battery → "Don't optimize"** (or "Unrestricted").  
Path varies by manufacturer:
- Samsung: **Device Care → Battery → Background usage limits → Never sleeping apps → Add Termux**
- Xiaomi/MIUI: **Settings → Battery & performance → Choose apps → Termux → No restrictions**

### Step 2 — Wake lock (CPU stays awake)

```bash
# Requires Termux:API app installed from F-Droid
pkg install -y termux-api

termux-wake-lock     # prevent CPU sleep
termux-wake-unlock   # release when done
```

### Step 3 — Wi-Fi always on

**Settings → Wi-Fi → Advanced → Keep Wi-Fi on during sleep → Always**

### Step 4 — Plug in

For 24/7 operation, plug the tablet into a charger. At 100% charge, disable "Battery saver" modes and set the display to turn off (not the CPU).

### Keep sessions alive with tmux

```bash
pkg install -y tmux

# Start a named session
tmux new -s server

# Detach (server keeps running)
Ctrl+B, then D

# Reattach later (from SSH or local terminal)
tmux attach -t server

# List sessions
tmux ls
```

---

## 10. Auto-Start on Reboot (Termux:Boot)

Install **Termux:Boot** from F-Droid. Then open it once to enable it.

Create your boot script:

```bash
mkdir -p ~/.termux/boot

cat > ~/.termux/boot/start-server.sh << 'EOF'
#!/data/data/com.termux/files/usr/bin/bash

# Prevent CPU sleep
termux-wake-lock

# Wait for network
sleep 5

# Start SSH server
sshd

# Start tmux session with your services
tmux new-session -d -s main

# Nginx
tmux send-keys -t main "nginx" Enter

# MariaDB
tmux send-keys -t main "mysqld_safe &" Enter

# Your Node app
tmux new-window -t main
tmux send-keys -t main "cd ~/nodeapp && node index.js" Enter

# proot-distro Ubuntu with its own services
# proot-distro login ubuntu -- /etc/init.d/nginx start
EOF

chmod +x ~/.termux/boot/start-server.sh
```

This script runs automatically after every reboot. Open Termux:Boot once manually to register it.

---

## 11. Termux:API — Tap Into Android Hardware

`termux-api` lets your shell scripts access Android's sensors and system features — useful for server-side automation.

```bash
pkg install -y termux-api
```

### Example commands

```bash
# Send a notification to the tablet's notification bar
termux-notification --title "Server Alert" --content "Nginx is down!"

# Get battery status as JSON
termux-battery-status

# Take a photo
termux-camera-photo ~/photo.jpg

# Get current GPS location
termux-location

# Text-to-speech
termux-tts-speak "Server is back online"

# Clipboard
echo "copied text" | termux-clipboard-set
termux-clipboard-get

# Torch / flashlight
termux-torch on
termux-torch off

# SMS (requires additional permissions)
termux-sms-send -n +91XXXXXXXXXX "Server is up"
```

### Monitoring + alert example

```bash
cat > ~/monitor.sh << 'EOF'
#!/data/data/com.termux/files/usr/bin/bash
while true; do
    if ! curl -s http://localhost:80 > /dev/null; then
        termux-notification --title "Alert" --content "Nginx is DOWN!"
        nginx   # attempt restart
    fi
    sleep 60
done
EOF
chmod +x ~/monitor.sh
# Run in background tmux window
```

---

## 12. Networking Cheatsheet

```bash
# Your tablet's local IP
ip addr show wlan0 | grep "inet "

# All listening ports
ss -tlnp
# or: netstat -tlnp

# Firewall — Android has no iptables restrictions for non-root Termux
# All ports you bind are accessible from the local network

# Port scan your own device (from another machine)
nmap -p 8022,8080,3000 192.168.1.105

# Check if a port is open
nc -zv 192.168.1.105 8022

# Port forwarding — forward traffic from your router to the tablet
# (done in your router's admin panel, not Termux)
# External :80 → Tablet :8080 (example)

# Tailscale VPN — simplest way to reach the tablet from anywhere
pkg install -y termux-api   # needed for tailscale auth
curl -fsSL https://tailscale.com/install.sh | sh
tailscale up
# After this your tablet has a stable 100.x.x.x address from any device
```

---

## 13. Useful Tools & Aliases

Add to `~/.bashrc` or `~/.zshrc`:

```bash
# ---- Aliases ----
alias ll='ls -la'
alias ..='cd ..'
alias ports='ss -tlnp'
alias myip='ip addr show wlan0 | grep "inet " | awk "{print \$2}"'

# Service shortcuts
alias start-ssh='pkill sshd 2>/dev/null; sshd && echo "sshd started on :8022"'
alias start-nginx='nginx && echo "nginx started on :8080"'
alias stop-nginx='nginx -s stop'
alias start-db='mysqld_safe > /dev/null 2>&1 &'

# proot shortcuts
alias ubuntu='proot-distro login ubuntu'
alias debian='proot-distro login debian'

# Wakelock
alias stay-awake='termux-wake-lock && echo "Wake lock acquired"'

# tmux
alias att='tmux attach -t server || tmux new -s server'
```

### Handy one-liners

```bash
# Watch live HTTP access log
tail -f $PREFIX/var/log/nginx/access.log

# Disk usage — see what's eating storage
du -sh ~/* | sort -rh | head -20

# RAM usage
free -h

# CPU + process info
htop

# Current network connections
ss -tnp

# Generate a self-signed TLS cert (for HTTPS locally)
openssl req -x509 -newkey rsa:4096 -keyout key.pem -out cert.pem -days 365 -nodes -subj "/CN=localhost"
```

---

## 14. Limitations

Understanding what Termux *cannot* do without root:

| Feature | Limitation | Workaround |
|---------|-----------|-----------|
| Ports < 1024 | Cannot bind port 22, 80, 443 | Use 8022, 8080, 8443 or a reverse proxy |
| `systemd` | Not available (Android doesn't run systemd) | Start services manually or via Termux:Boot script |
| Docker | Requires kernel namespaces — not available without root | Use Linux Deploy on a rooted device |
| `cgroups` | Limited access | Can't run containers natively |
| `/proc` / `/sys` | Read-only from proot | Full access requires root |
| Background process limits | Android may still kill Termux if under memory pressure | Ensure battery optimization is disabled; use wake lock |
| IPv6 | May not work on all ROMs | Use IPv4 for local services |
| NFS / FUSE mounts | Not supported without root | Use Samba or SSH (SFTP) for file sharing |

---

## Quick Reference Card

```
Install Termux:      F-Droid only
Update packages:     pkg update && pkg upgrade
Install SSH:         pkg install openssh && sshd
Your IP:             ip addr show wlan0 | grep inet
SSH from laptop:     ssh -p 8022 <tablet-ip>
Enter Ubuntu:        proot-distro login ubuntu
Prevent sleep:       termux-wake-lock
Auto-start:          ~/.termux/boot/start-server.sh  +  Termux:Boot app
Persistent session:  tmux new -s server
Web root (nginx):    $PREFIX/share/nginx/html
Config dir:          $PREFIX/etc/
Home dir:            /data/data/com.termux/files/home  (~)
Android storage:     ~/storage/shared  (after termux-setup-storage)
```
