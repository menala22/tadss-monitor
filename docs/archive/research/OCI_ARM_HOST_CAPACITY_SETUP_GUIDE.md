# OCI ARM Host Capacity - Setup Guide

**Tool:** [oci-arm-host-capacity](https://github.com/hitrov/oci-arm-host-capacity)  
**Purpose:** Automatically reserve Oracle Cloud ARM capacity (VM.Standard.A1.Flex)  
**Created:** March 4, 2026  
**Language:** PHP (requires PHP + Composer)

---

## What This Tool Does

This PHP script automatically retries Oracle Cloud ARM instance creation until capacity becomes available. It solves the common **"Out of host capacity"** error by:

- ✅ Repeatedly calling OCI API until capacity is found
- ✅ Supporting up to 4 OCPUs + 24GB RAM (Always Free tier)
- ✅ Checking existing instances to avoid exceeding limits
- ✅ Running as cron job or GitHub Actions workflow
- ✅ Supporting multiple configurations/accounts

---

## Prerequisites

| Requirement | How to Check | How to Install |
|-------------|--------------|----------------|
| **PHP 7.x or 8.x** | `php --version` | `brew install php` (macOS) |
| **Composer** | `composer --version` | `brew install composer` (macOS) |
| **OCI CLI** (optional) | `oci --version` | `brew install oci-cli` |
| **Git** | `git --version` | `brew install git` |

---

## Installation

### Step 1: Install PHP and Composer

```bash
# macOS (Homebrew)
brew install php
brew install composer

# Verify installation
php --version
composer --version
```

### Step 2: Clone the Repository

```bash
# Clone to your home directory or projects folder
cd ~
git clone https://github.com/hitrov/oci-arm-host-capacity.git
cd oci-arm-host-capacity

# Install PHP dependencies
composer install
```

### Step 3: Generate OCI API Key

1. **Log into Oracle Cloud Console:** https://cloud.oracle.com/

2. **Navigate to API Keys:**
   - Click your **Profile Icon** (top-right)
   - Select **User Settings**

3. **Generate API Key:**
   - Go to **Resources** → **API keys**
   - Click **Add API Key**
   - Select **Generate API Key Pair**
   - Click **Download Private Key** (save as `oci_api_key.pem`)
   - **Copy the configuration text** from the textarea (you'll need this)

4. **Save the Private Key:**
   ```bash
   # Move to secure location
   mkdir -p ~/.oci
   mv ~/Downloads/oci_api_key.pem ~/.oci/
   
   # Set secure permissions
   chmod 600 ~/.oci/oci_api_key.pem
   ```

### Step 4: Configure Environment File

```bash
# Navigate to project directory
cd ~/oci-arm-host-capacity

# Copy example environment file
cp .env.example .env

# Edit configuration
nano .env
```

---

## Configuration (.env File)

### Required Settings

| Variable | Description | Where to Find |
|----------|-------------|---------------|
| `OCI_REGION` | OCI region identifier | From API key config text |
| `OCI_USER_ID` | User OCID | From API key config text |
| `OCI_TENANCY_ID` | Tenancy OCID | From API key config text |
| `OCI_KEY_FINGERPRINT` | API key fingerprint | From API key config text |
| `OCI_PRIVATE_KEY_FILENAME` | Path to `.pem` file | `~/.oci/oci_api_key.pem` |
| `OCI_SUBNET_ID` | Subnet OCID | From browser DevTools (see below) |
| `OCI_IMAGE_ID` | Image OCID | From browser DevTools (see below) |
| `OCI_SSH_PUBLIC_KEY` | SSH public key content | `cat ~/.ssh/id_rsa.pub` |

### Optional Settings

| Variable | Default | Description |
|----------|---------|-------------|
| `OCI_OCPUS` | `4` | OCPU count (1-4 for ARM) |
| `OCI_MEMORY_IN_GBS` | `24` | Memory in GB (6-24 for ARM) |
| `OCI_MAX_INSTANCES` | `1` | Maximum instances to create |
| `OCI_AVAILABILITY_DOMAIN` | *(auto)* | Specific AD to use |
| `OCI_SHAPE` | `VM.Standard.A1.Flex` | Instance shape |

### Example .env File

```env
# OCI API Configuration
OCI_REGION=us-ashburn-1
OCI_USER_ID=ocid1.user.oc1..xxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxx
OCI_TENANCY_ID=ocid1.tenancy.oc1..xxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxx
OCI_KEY_FINGERPRINT=xx:xx:xx:xx:xx:xx:xx:xx:xx:xx:xx:xx:xx:xx:xx:xx

# Private Key Path (absolute path or URL)
OCI_PRIVATE_KEY_FILENAME=/Users/yourusername/.oci/oci_api_key.pem

# Network and Image (from DevTools - see below)
OCI_SUBNET_ID=ocid1.subnet.oc1..xxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxx
OCI_IMAGE_ID=ocid1.image.oc1..xxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxx

# SSH Public Key (single line, no newlines)
OCI_SSH_PUBLIC_KEY=ssh-rsa AAAAB3NzaC1yc2EAAAADAQABAAABAQ... your-email@example.com

# Instance Configuration (ARM Free Tier)
OCI_OCPUS=4
OCI_MEMORY_IN_GBS=24
OCI_MAX_INSTANCES=1
OCI_SHAPE=VM.Standard.A1.Flex
```

---

## Getting OCI_SUBNET_ID and OCI_IMAGE_ID

This is the **tricky part** - you need to extract these from browser DevTools:

### Step 1: Open Instance Creation Page

1. Go to Oracle Cloud Console → **Compute** → **Instances**
2. Click **Create Instance**

### Step 2: Configure Instance

1. **Compartment:** Select your compartment
2. **Availability Domain:** Choose any (AD-1, AD-2, or AD-3)
3. **Image:** Select **Canonical Ubuntu 22.04 Minimal Aarch64** (or your preferred ARM image)
4. **Shape:** Select **VM.Standard.A1.Flex** (ARM)
5. **Networking:**
   - Create new VCN or select existing
   - **Uncheck** "Assign a public IPv4 address" (for security)
6. **SSH Keys:** Paste your public key content

### Step 3: Open Browser DevTools

1. Press **F12** (or right-click → Inspect)
2. Go to **Network** tab
3. Check **Preserve log**

### Step 4: Trigger API Call

1. Click **Create** button
2. You'll see a **red (failed)** API call to `/instances`
3. Right-click the call → **Copy** → **Copy as cURL**

### Step 5: Extract IDs

1. Paste the cURL command into a text editor
2. Look for `data-binary` or `payload` section
3. Find these values:
   ```json
   {
     "subnetId": "ocid1.subnet.oc1..xxxxxxxxxxxxx",
     "imageId": "ocid1.image.oc1..xxxxxxxxxxxxx",
     ...
   }
   ```
4. Copy these OCIDs to your `.env` file

---

## Running the Tool

### Basic Execution

```bash
# Navigate to project directory
cd ~/oci-arm-host-capacity

# Run the script
php ./index.php
```

### Expected Output

**Capacity Unavailable (Retry):**
```json
{
    "code": "InternalError",
    "message": "Out of host capacity."
}
```

**Limit Exceeded:**
```json
{
    "code": "LimitExceeded",
    "message": "The following service limits were exceeded: standard-a1-memory-count, standard-a1-core-count..."
}
```

**Success - Instance Created:**
```json
{
    "id": "ocid1.instance.oc1.xxxxxx",
    "displayName": "instance-20260304-xxxx",
    "publicIp": null,
    ...
}
```

### Running with Custom Environment File

```bash
# Use a different .env file (e.g., for multiple accounts)
php index.php .env.my_acc1
```

---

## Automated Execution (Cron Job)

### Setup Cron Job (Linux/macOS)

```bash
# Create log file
touch ~/oci-arm-host-capacity/oci.log
chmod 644 ~/oci-arm-host-capacity/oci.log

# Find PHP path
which php
# Output: /opt/homebrew/bin/php or /usr/bin/php

# Edit crontab
crontab -e

# Add line to run every minute
* * * * * /opt/homebrew/bin/php /Users/yourusername/oci-arm-host-capacity/index.php >> /Users/yourusername/oci-arm-host-capacity/oci.log 2>&1
```

### Verify Cron Job

```bash
# List cron jobs
crontab -l

# Check logs
tail -f ~/oci-arm-host-capacity/oci.log
```

### Remove Cron Job

```bash
# Edit crontab and remove the line
crontab -e

# Or remove all cron jobs
crontab -r
```

---

## GitHub Actions (Alternative to Cron)

### Setup Steps

1. **Fork the repository** to your GitHub account

2. **Add Repository Secrets:**
   - Go to your fork → **Settings** → **Secrets and variables** → **Actions**
   - Add all `.env` variables as secrets:
     - `OCI_REGION`
     - `OCI_USER_ID`
     - `OCI_TENANCY_ID`
     - `OCI_KEY_FINGERPRINT`
     - `OCI_PRIVATE_KEY_FILENAME` (URL to key)
     - `OCI_SUBNET_ID`
     - `OCI_IMAGE_ID`
     - `OCI_SSH_PUBLIC_KEY`

3. **Upload Private Key:**
   - Upload `oci_api_key.pem` to a private OCI Object Storage bucket
   - Create a **pre-authenticated URL** (PAR)
   - Set `OCI_PRIVATE_KEY_FILENAME` secret to the PAR URL

4. **Enable GitHub Actions:**
   - Go to **Actions** tab
   - Enable workflows if needed

### ⚠️ Important GitHub Actions Warning

**Delete test workflow after verification:**
```bash
# Remove tests.yml to avoid GitHub Terms of Service violations
rm .github/workflows/tests.yml
git add .github/workflows/tests.yml
git commit -m "Remove test workflow"
git push
```

**Reason:** Leaving scheduled workflows running indefinitely violates GitHub Terms of Use.

---

## After Instance Creation

### Step 1: Assign Public IP (Optional)

If you didn't assign a public IP during creation:

1. Go to **Instance Details** → **Attached VNICs**
2. Click the VNIC
3. **IPv4 Addresses** → **Edit**
4. Select **Ephemeral** → **Update**

### Step 2: SSH into Instance

```bash
# With public IP
ssh -i ~/.ssh/id_rsa opc@YOUR.PUBLIC.IP

# With private IP/FQDN (from same VCN)
ssh -i ~/.ssh/id_rsa opc@instance-20260304-xxxx.subnet.vcn.oraclevcn.com
```

### Step 3: Stop the Script

Once instance is created, **stop the cron job or script** to avoid creating duplicate instances:

```bash
# Remove cron job
crontab -e
# Remove or comment out the oci-arm-host-capacity line

# Or kill running process
ps aux | grep "php index.php"
kill <PID>
```

---

## Troubleshooting

### Private Key Issues

**Error:** `PrivateKeyFileNotFoundException`

```bash
# Solution: Ensure path is absolute
OCI_PRIVATE_KEY_FILENAME=/Users/yourusername/.oci/oci_api_key.pem

# Or use URL (if hosted on OCI Object Storage)
OCI_PRIVATE_KEY_FILENAME="https://objectstorage.us-ashburn-1.oraclecloud.com/p/xxxxxx"
```

**Error:** `Permission denied`

```bash
# Fix permissions
chmod 600 ~/.oci/oci_api_key.pem
```

### SSH Key Issues

**Error:** `InvalidParameter - Unable to parse message body`

**Cause:** Newlines in `OCI_SSH_PUBLIC_KEY`

**Solution:**
```bash
# Copy as single line
cat ~/.ssh/id_rsa.pub | tr -d '\n' | pbcopy

# Then paste into .env
OCI_SSH_PUBLIC_KEY=ssh-rsa AAAAB3... (single line)
```

**Error:** `Invalid ssh public key; must be in base64 format`

**Solution:** Regenerate SSH keys:
```bash
ssh-keygen -t rsa -b 4096 -f ~/.ssh/id_rsa
cat ~/.ssh/id_rsa.pub | pbcopy
```

### Subnet/Image ID Issues

**Error:** `Invalid subnet ID` or `Invalid image ID`

**Solution:**
1. Re-extract IDs from DevTools
2. Ensure you're using the correct region
3. Verify image supports ARM (Aarch64)

### Limit Exceeded

**Error:** `LimitExceeded - standard-a1-core-count`

**Solution:**
- You've reached the free tier limit (4 OCPUs total)
- Delete unused ARM instances
- Or request limit increase in OCI Console

---

## Valid ARM Configurations

| OCI_OCPUS | OCI_MEMORY_IN_GBS | Shape |
|-----------|-------------------|-------|
| 1 | 6 | VM.Standard.A1.Flex |
| 2 | 12 | VM.Standard.A1.Flex |
| 3 | 18 | VM.Standard.A1.Flex |
| 4 | 24 | VM.Standard.A1.Flex |

**Note:** Memory must be 6 GB per OCPU for ARM instances.

---

## Alternative: AMD x86 Configuration

If ARM capacity is consistently unavailable:

```env
OCI_SHAPE=VM.Standard.E2.1.Micro
OCI_OCPUS=1
OCI_MEMORY_IN_GBS=1
OCI_AVAILABILITY_DOMAIN=FeVO:EU-FRANKFURT-1-AD-2
```

**Note:** x86 instances have much lower free tier limits (1 OCPU, 1 GB RAM).

---

## Security Best Practices

### 1. Protect Your .env File

```bash
# Never commit .env to Git
echo ".env" >> .gitignore

# Set restrictive permissions
chmod 600 .env

# Never share or upload .env
```

### 2. Protect Private Key

```bash
# Secure permissions
chmod 600 ~/.oci/oci_api_key.pem

# Store in secure location
# Never share or commit
```

### 3. Use SSH Keys (Not Passwords)

```bash
# Generate strong SSH key
ssh-keygen -t ed25519 -a 100 -f ~/.ssh/id_rsa

# Copy public key
cat ~/.ssh/id_rsa.pub | pbcopy
```

### 4. Restrict Network Access

After instance creation:
- Configure Oracle Cloud Security Lists
- Enable UFW firewall on instance
- Restrict SSH to your IP only

---

## Monitoring and Logs

### View Script Logs

```bash
# Tail cron log
tail -f ~/oci-arm-host-capacity/oci.log

# Search for success messages
grep -i "success" ~/oci-arm-host-capacity/oci.log

# Search for errors
grep -i "error" ~/oci-arm-host-capacity/oci.log
```

### Check OCI Console

1. Go to **Compute** → **Instances**
2. Look for new instances with status **Running**
3. Note the public IP address

---

## Quick Reference Commands

```bash
# Install dependencies (first time only)
brew install php composer git

# Clone repository
cd ~
git clone https://github.com/hitrov/oci-arm-host-capacity.git
cd oci-arm-host-capacity
composer install

# Configure
cp .env.example .env
nano .env

# Run manually
php ./index.php

# Setup cron
crontab -e
# Add: * * * * * /opt/homebrew/bin/php /Users/username/oci-arm-host-capacity/index.php >> ~/oci-arm-host-capacity/oci.log 2>&1

# View logs
tail -f ~/oci-arm-host-capacity/oci.log

# Stop after success
crontab -e  # Remove or comment out the line
```

---

## Pay As You Go (PAYG) Recommendation

**Consider upgrading to PAYG:**
- ✅ **Priority** for instance launches
- ✅ **Reduced** "Out of capacity" errors
- ✅ **Same free tier** benefits (4 OCPUs + 24GB RAM free)
- ✅ **Pay only** for usage beyond free tier

**Set budget alerts** to monitor spending:
1. Go to **Governance & Administration** → **Cost Management**
2. Create **Budget** with $0-10 limit
3. Set email alerts

---

## Related Files

| File | Purpose |
|------|---------|
| `index.php` | Main script |
| `.env.example` | Configuration template |
| `.env` | Your configuration (create from example) |
| `composer.json` | PHP dependencies |
| `.github/workflows/` | GitHub Actions workflows |

---

## Useful Links

- **Repository:** https://github.com/hitrov/oci-arm-host-capacity
- **OCI Console:** https://cloud.oracle.com/
- **OCI Documentation:** https://docs.oracle.com/en-us/iaas/
- **Free Tier Limits:** https://www.oracle.com/cloud/free/

---

## Summary

| Step | Command | Status |
|------|---------|--------|
| 1. Install PHP + Composer | `brew install php composer` | ⬜ |
| 2. Clone repository | `git clone https://github.com/hitrov/oci-arm-host-capacity.git` | ⬜ |
| 3. Install dependencies | `composer install` | ⬜ |
| 4. Generate OCI API key | User Settings → API keys | ⬜ |
| 5. Configure .env | `cp .env.example .env && nano .env` | ⬜ |
| 6. Extract Subnet/Image IDs | Browser DevTools | ⬜ |
| 7. Run script | `php ./index.php` | ⬜ |
| 8. Setup cron (optional) | `crontab -e` | ⬜ |
| 9. Stop after success | Remove cron job | ⬜ |

---

**Last Updated:** March 4, 2026  
**Tool Version:** Latest (check GitHub for updates)  
**Status:** Ready to deploy
