# Getting your Danfoss Link credentials

Home Assistant needs the same three pieces of data the **Danfoss Link Android app** uses to reach your central controller (CC) through Danfoss cloud.

You will **not** find these in the CC web UI or by scanning your Wi‑Fi. They live **inside the app’s private storage** on Android.

---

## The three values (checklist)

Copy these somewhere safe (password manager or encrypted folder). **Never commit them to GitHub or share them publicly.**

| # | Name in HA setup | File on Android (typical) |
|---|------------------|---------------------------|
| 1 | App certificate (PEM) | `app_cert.pem` |
| 2 | App private key (PEM) | `app_key.pem` |
| 3 | CC peer ID | Inside `pairings/` (see below) |

**CC peer ID** looks like:

```text
e7:af:e3:77:61:90:0d:b5:1f:87:d9:7c:ea:da:10:1e:25:26:9b:a1
```

You can also paste the pairing **filename** with underscores (e.g. `e7_af_e3_77_...`) — Home Assistant accepts that format.

---

## Method A — Android emulator (recommended)

Best if you use Home Assistant on a Raspberry Pi or NAS and **do not** want to root your daily phone. You only need a Windows, Mac, or Linux PC **once** to run the emulator.

### What you will install

- **Android Studio** (free) — includes the emulator and `adb` tool.

### Step 1 — Install Android Studio

1. Download from [developer.android.com/studio](https://developer.android.com/studio).
2. Run the installer with default options.
3. Open Android Studio → complete the first-run wizard (SDK download is normal).

### Step 2 — Create a virtual phone

1. Open **Device Manager** (phone icon on the welcome screen, or **Tools → Device Manager**).
2. Click **Create Virtual Device**.
3. Pick a phone model (e.g. **Pixel 6**) → **Next**.
4. Choose a **system image**:
   - **Release name:** API **34** (or newer with Google Play).
   - **ABI:** **arm64-v8a** (important — Danfoss app uses native ARM libraries).
   - Tab **Google Play** — pick an image that shows the **Play Store** icon.
5. Download the image if asked → **Next** → **Finish**.

### Step 3 — Start the emulator and sign in to Google

1. Press **▶ (Run)** on your virtual device.
2. Wait until the Android home screen appears.
3. Open **Play Store**, sign in with a Google account (any account you use for apps is fine).

### Step 4 — Install Danfoss Link and pair with your CC

1. In Play Store, install **Danfoss Link** (publisher Danfoss).
2. Open the app and go through setup until it finds your **CC** and pairing completes — same steps as on a real phone.
3. Confirm you can see **rooms and temperatures** in the app.

**Network tips:**

- Your **home Wi‑Fi** must be the same network your **CC** uses (same as when you set up the phone app today).
- The emulator uses your PC’s network; if discovery fails, check firewall/VLAN rules (CC and PC must reach each other and the internet).

**Optional but useful:** In Device Manager, use **⋮ → Snapshots** and save a snapshot named `paired` after success. Do **not** use “Wipe data” on that AVD later, or you will need to pair again.

### Step 5 — Install platform tools (`adb`) on your PC

Android Studio usually installs `adb`. To run it from a terminal:

- **Mac/Linux:** often  
  `~/Library/Android/sdk/platform-tools/adb`  
  or `$ANDROID_HOME/platform-tools/adb`
- **Windows:**  
  `%LOCALAPPDATA%\Android\Sdk\platform-tools\adb.exe`

Add that folder to your PATH, or use the full path in commands below.

Check the emulator is visible:

```bash
adb devices
```

You should see one device listed as `device` (not `offline`).

### Step 6 — Pull credentials with the helper script

From this repository:

```bash
cd scripts
chmod +x pull_danfoss_creds.sh
./pull_danfoss_creds.sh ~/danfoss_link_creds
```

The script will:

1. Run `adb root` (works on the **emulator**; may fail on a normal phone).
2. Copy `app_cert.pem`, `app_key.pem`, and pairing files from the app data directory.
3. Print your **CC peer ID** and where files were saved.

**If the script says “luadata not found”:** open the app once on the emulator, wait until it connects, then run the script again.

### Step 7 — Keep these files for Home Assistant

You should have a folder like `~/danfoss_link_creds` containing:

```text
app_cert.pem
app_key.pem
pairings/          (optional; peer ID is printed by the script)
SUMMARY.txt        (peer ID and paths — created by the script)
```

You can **close the emulator**. Credentials remain valid for HA.

**Important:** While Home Assistant is using these credentials, **do not** open Danfoss Link on the emulator (or on another device using the **same** cert). Only one active connection at a time is safe.

---

## Method B — Rooted phone + USB debugging

Use this if you already have a **rooted** Android phone with Danfoss Link **already paired**.

1. Enable **Developer options** → **USB debugging**.
2. Connect USB → accept debugging prompt.
3. Verify: `adb devices`
4. Run the same script:

   ```bash
   ./pull_danfoss_creds.sh ~/danfoss_link_creds
   ```

If `adb root` fails, your phone is not rooted enough — use **Method A (emulator)** instead.

---

## Method C — Manual `adb` commands (no script)

Package name: `com.danfoss.linkapp`

Typical data paths (app version may use `files/` or `files/luadata/`):

```text
/data/data/com.danfoss.linkapp/files/luadata/app_cert.pem
/data/data/com.danfoss.linkapp/files/luadata/app_key.pem
/data/data/com.danfoss.linkapp/files/luadata/pairings/
```

Commands (emulator or rooted device):

```bash
adb root
adb shell "ls -la /data/data/com.danfoss.linkapp/files/luadata/"
mkdir -p ~/danfoss_link_creds
adb pull /data/data/com.danfoss.linkapp/files/luadata/app_cert.pem ~/danfoss_link_creds/
adb pull /data/data/com.danfoss.linkapp/files/luadata/app_key.pem ~/danfoss_link_creds/
adb pull /data/data/com.danfoss.linkapp/files/luadata/pairings/ ~/danfoss_link_creds/pairings/
```

**Peer ID from filename:** each file in `pairings/` is named with underscores instead of colons.

**Peer ID from file content:** open the pairing file in a text editor and find the line:

```text
["peer_id"]="e7:af:e3:..."
```

---

## What you do *not* need

| Myth | Reality |
|------|---------|
| CC IP address on LAN | Not used by this integration |
| SSH into the CC | CC does not expose user API over LAN in typical setups |
| Danfoss cloud account password | Not stored in these PEM files; pairing is bound to app cert |
| Re-pairing when HA runs | Only if you factory-reset the CC or remove pairing in the app |

---

## Next step

Go to [home-assistant-setup.md](home-assistant-setup.md) to install the integration and enter these three values.

If something fails, see [troubleshooting.md](troubleshooting.md).
