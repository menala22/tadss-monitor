# VPS Providers Comparison Report 2026

**For:** TA-DSS Trading Order Monitoring System  
**Research Date:** March 3, 2026  
**Purpose:** Find suitable VPS hosting while Oracle Cloud ARM capacity is unavailable  

---

## Executive Summary

This report compares **15+ VPS providers** across free tier, budget, and premium options for hosting the TA-DSS application. Key findings:

| Category | Best Option | Price | Why |
|----------|-------------|-------|-----|
| **Best Free Tier** | Oracle Cloud | $0/month | 4 OCPU + 24GB RAM (but capacity issues) |
| **Best Budget** | Hetzner | €4.99/month | 4 vCPU + 8GB RAM, excellent value |
| **Best for Asia** | Alibaba Cloud | $8.5/month | Low latency to Asia-Pacific |
| **Best Trial** | DigitalOcean | $200/60 days | Longest trial period |
| **Best Vietnam** | Viettel | $21.45/month | Local presence, low latency |

---

## Table of Contents

1. [Free Tier Providers](#1-free-tier-providers)
2. [Budget VPS Providers (Under $10/month)](#2-budget-vps-providers-under-10month)
3. [Mid-Range Providers ($10-30/month)](#3-mid-range-providers-10-30month)
4. [Vietnamese Providers](#4-vietnamese-providers)
5. [Asian Providers](#5-asian-providers)
6. [European Providers](#6-european-providers)
7. [US Providers](#7-us-providers)
8. [Recommendations for TA-DSS](#8-recommendations-for-ta-dss)

---

## 1. Free Tier Providers

### 1.1 Oracle Cloud Free Tier ⭐ **Recommended**

| Specification | Value |
|---------------|-------|
| **Compute** | 4 OCPU + 24 GB RAM (ARM Ampere A1) |
| **Alternative** | 2 × (1/8 OCPU + 1 GB RAM) AMD VMs |
| **Storage** | 200 GB Block Volume total |
| **Network** | Up to 10 TB outbound/month |
| **Database** | 2 × 20 GB Autonomous Database |
| **Trial Credit** | $300 for 30 days |
| **Duration** | **Always Free** (unlimited time) |

**Pros:**
- ✅ **Most generous free tier** (4 CPU + 24GB RAM)
- ✅ **Truly free forever** (no expiration)
- ✅ **10 TB/month** outbound traffic
- ✅ **ARM architecture** (perfect for our Docker setup)
- ✅ Enterprise-grade infrastructure

**Cons:**
- ❌ **Capacity issues** in popular regions (Japan, Korea, some US regions)
- ❌ **Difficult registration** (high rejection rate)
- ❌ **Strict verification** (credit card, phone)
- ❌ **Complex UI** for beginners

**Best For:** Production deployment (when capacity available)

**TA-DSS Fit:** ⭐⭐⭐⭐⭐ (Perfect - this is our target)

---

### 1.2 Google Cloud Platform (GCP) Free Tier

| Specification | Value |
|---------------|-------|
| **Compute** | 1 × e2-micro (1 vCPU shared, 0.6 GB RAM) |
| **Storage** | 30 GB standard persistent disk |
| **Network** | 1 GB egress/month |
| **Regions** | us-central1, us-west1, us-east1 only |
| **Trial Credit** | $300 for 90 days |
| **Duration** | Always Free (1 instance) |

**Pros:**
- ✅ **Permanent free tier** (no expiration)
- ✅ Reliable infrastructure
- ✅ $300 trial credit for 90 days
- ✅ 20+ other free products

**Cons:**
- ❌ **Very limited resources** (0.6 GB RAM)
- ❌ **Only 1 GB egress/month** (major limitation)
- ❌ **US regions only** for free tier
- ❌ May require $10 security deposit

**Best For:** Testing, very lightweight apps

**TA-DSS Fit:** ⭐⭐ (Insufficient RAM for our app)

---

### 1.3 AWS Free Tier

| Specification | Value |
|---------------|-------|
| **EC2 (12 months)** | 750 hours/month t2.micro or t3.micro |
| **Lambda (Always)** | 1M requests + 3.2M GB-seconds/month |
| **DynamoDB (Always)** | 25 GB storage + 200M requests/month |
| **S3 (Always)** | 5 GB standard storage |
| **Trial Credit** | Up to $200 (12 months) |
| **Duration** | 12 months for VM, unlimited for serverless |

**Pros:**
- ✅ **30+ Always Free services**
- ✅ **12 months** of free EC2 usage
- ✅ Industry-leading infrastructure
- ✅ Comprehensive documentation

**Cons:**
- ❌ **Only 12 months** for VM (not permanent)
- ❌ **Limited to micro instances** (1 GB RAM)
- ❌ Must monitor usage carefully
- ❌ EIP charges if not attached (~$3.60/month)

**Best For:** Learning cloud, serverless apps

**TA-DSS Fit:** ⭐⭐⭐ (Good for 1 year, then paid)

---

### 1.4 Microsoft Azure Free Tier

| Specification | Value |
|---------------|-------|
| **VM (12 months)** | B-series VMs, 750 hours/month |
| **Functions (Always)** | 1M executions/month |
| **App Service (Always)** | 10 web/mobile/API apps |
| **Storage (12 months)** | 5 GB Blob + 5 GB File |
| **Trial Credit** | $200 for 30 days |
| **Duration** | 12 months for VM, unlimited for serverless |

**Pros:**
- ✅ **Both Windows and Linux** VMs
- ✅ **$200 credit** for 30 days
- ✅ 40+ services free for 12 months
- ✅ Student benefits ($100/year recurring)

**Cons:**
- ❌ **750 hours/month limit** (~25 hours/day)
- ❌ **Only 12 months** free
- ❌ Must upgrade to pay-as-you-go within 30 days
- ❌ Complex pricing structure

**Best For:** Windows apps, Microsoft stack learning

**TA-DSS Fit:** ⭐⭐⭐ (Good for 1 year, then paid)

---

### 1.5 IBM Cloud Lite

| Specification | Value |
|---------------|-------|
| **Compute** | 1 vCPU, 1 GB storage |
| **Products** | 40+ forever-free products |
| **Users** | 1 user limit |
| **Duration** | Always Free |

**Pros:**
- ✅ **Forever free** (no expiration)
- ✅ 40+ products available
- ✅ Enterprise-grade infrastructure
- ✅ Good for learning

**Cons:**
- ❌ **Only 1 vCPU with 1 GB storage**
- ❌ **Single user limit**
- ❌ Not suitable for production

**TA-DSS Fit:** ⭐ (Insufficient resources)

---

### 1.6 Render (Forever Free)

| Specification | Value |
|---------------|-------|
| **CPU/RAM** | 0.1 vCPU, 512 MB RAM |
| **Bandwidth** | 100 GB/month (inbound unlimited) |
| **Storage** | Extra cost ($0.25/GB/month) |
| **Duration** | Always Free |

**Pros:**
- ✅ **Forever free** (no expiration)
- ✅ Auto-deploy from Git
- ✅ Free DDoS protection
- ✅ Email support included

**Cons:**
- ❌ **Extremely limited** (0.1 vCPU, 512 MB RAM)
- ❌ **Storage costs extra**
- ❌ App **sleeps after 15 min** inactivity
- ❌ Unmanaged service

**TA-DSS Fit:** ⭐ (Insufficient resources, sleep mode breaks scheduler)

---

## 2. Budget VPS Providers (Under $10/month)

### 2.1 Hetzner Cloud ⭐ **Best Value**

| Plan | Price | vCPU | RAM | SSD | Traffic |
|------|-------|------|-----|-----|---------|
| **CPX11** | €4.99/month | 2 | 2 GB | 40 GB | 20 TB |
| **CPX21** | €9.99/month | 3 | 4 GB | 80 GB | 24 TB |
| **CX22** | €5.99/month | 2 | 4 GB | 40 GB | 20 TB |

**Locations:** Germany (Nuremberg, Falkenstein), Finland (Helsinki), US (Ashburn, VA)

**Pros:**
- ✅ **Best price/performance ratio** in Europe
- ✅ **High traffic allowance** (20+ TB/month)
- ✅ **German quality** hardware
- ✅ Hourly billing available
- ✅ Instant provisioning

**Cons:**
- ❌ **High latency for Asia** (200-300ms)
- ❌ May require **address verification**
- ❌ Limited data center locations
- ❌ Support in German/English only

**TA-DSS Fit:** ⭐⭐⭐⭐⭐ (Excellent value, perfect for Europe deployment)

---

### 2.2 Vultr

| Plan | Price | vCPU | RAM | SSD | Traffic |
|------|-------|------|-----|-----|---------|
| **Cloud Compute** | $5/month | 1 | 1 GB | 32 GB | 1 TB |
| **High Frequency** | $6/month | 1 | 1 GB | 32 GB | 1 TB |
| **Dedicated** | $30/month | 2 | 8 GB | 128 GB | 5 TB |

**Locations:** 32 locations worldwide (Tokyo, Singapore, LA, Seattle, NY, London, Frankfurt, Amsterdam, Sydney)

**Pros:**
- ✅ **Global presence** (32 data centers)
- ✅ **Hourly billing** (pay only for what you use)
- ✅ **High Frequency** plans available (3.4+ GHz)
- ✅ One-click app marketplace
- ✅ Good API support

**Cons:**
- ❌ **More expensive** than Hetzner for same specs
- ❌ Traffic limits lower than competitors
- ❌ No ARM instances

**TA-DSS Fit:** ⭐⭐⭐⭐ (Good global coverage, reasonable price)

---

### 2.3 DigitalOcean

| Plan | Price | vCPU | RAM | SSD | Traffic |
|------|-------|------|-----|-----|---------|
| **Basic Droplet** | $6/month | 1 | 1 GB | 25 GB | 1 TB |
| **Basic Droplet** | $12/month | 1 | 2 GB | 50 GB | 2 TB |
| **Premium Droplet** | $24/month | 2 | 4 GB | 80 GB | 4 TB |

**Locations:** 8 regions (NYC, SFO, LON, AMS, FRA, SGP, BLR, TOR)

**Pros:**
- ✅ **Excellent documentation** and tutorials
- ✅ **Mature ecosystem** (350+ apps in Marketplace)
- ✅ **99.99% uptime guarantee**
- ✅ **60-day trial** with $200 credit
- ✅ Hatch program for startups (3 months free)

**Cons:**
- ❌ **More expensive** than Hetzner/Vultr
- ❌ **Limited to 8 regions**
- ❌ No ARM instances
- ❌ No money-back guarantee

**TA-DSS Fit:** ⭐⭐⭐⭐ (Great for developers, good documentation)

---

### 2.4 Linode (Akamai Cloud)

| Plan | Price | vCPU | RAM | SSD | Traffic |
|------|-------|------|-----|-----|---------|
| **Nanode** | $5/month | 1 | 1 GB | 25 GB | 1 TB |
| **Standard** | $10/month | 1 | 2 GB | 50 GB | 2 TB |
| **Dedicated** | $40/month | 4 | 8 GB | 160 GB | 5 TB |

**Locations:** 11 regions worldwide

**Pros:**
- ✅ **Long-term stability** (since 2003)
- ✅ **All SSD storage**
- ✅ **Free backup service**
- ✅ Excellent network performance
- ✅ Comprehensive API

**Cons:**
- ❌ **Pricier** than Hetzner
- ❌ **Limited regions** compared to Vultr
- ❌ No ARM instances

**TA-DSS Fit:** ⭐⭐⭐⭐ (Reliable, good for long-term)

---

### 2.5 OVHcloud

| Plan | Price | vCPU | RAM | SSD | Traffic |
|------|-------|------|-----|-----|---------|
| **VPS-1** | $4.20/month | 1 | 2 GB | 20 GB | Unlimited |
| **VPS-2** | $8.40/month | 2 | 4 GB | 40 GB | Unlimited |
| **VPS-3** | $16.80/month | 4 | 8 GB | 80 GB | Unlimited |

**Locations:** 19 data centers (Europe, US, Canada, Asia-Pacific)

**Pros:**
- ✅ **Unlimited traffic** on all plans
- ✅ **Very affordable** entry-level plans
- ✅ **DDoS protection** included
- ✅ European data sovereignty

**Cons:**
- ❌ **Recent price increases** (2026)
- ❌ **Support quality** varies
- ❌ **Older hardware** in some locations
- ❌ Complex control panel

**TA-DSS Fit:** ⭐⭐⭐⭐ (Good value, unlimited traffic)

---

### 2.6 Scaleway

| Plan | Price | vCPU | RAM | SSD | Traffic |
|------|-------|------|-----|-----|---------|
| **BASIC2-A2C-4G** | €16.79/month | 2 | 4 GB | 80 GB | 750 GB |
| **POP2-HC-2C-4G** | €45.20/month | 2 | 4 GB | 200 GB | Unlimited |

**Locations:** France (Paris), Netherlands (Amsterdam)

**Pros:**
- ✅ **European provider** (GDPR compliant)
- ✅ **ARM instances** available (similar to Oracle)
- ✅ Good performance
- ✅ Integrated ecosystem (Object Storage, IoT, etc.)

**Cons:**
- ❌ **Limited locations** (Europe only)
- ❌ **Higher prices** than Hetzner
- ❌ Traffic limits on basic plans

**TA-DSS Fit:** ⭐⭐⭐ (Good ARM option if Oracle unavailable)

---

### 2.7 RackNerd

| Plan | Price | vCPU | RAM | SSD | Traffic |
|------|-------|------|-----|-----|---------|
| **Budget KVM** | $10.88/year | 1 | 768 MB | 15 GB | 1 TB |
| **Standard** | $20/year | 2 | 2 GB | 40 GB | 3 TB |

**Locations:** US only (LA, NY, Dallas, Chicago, Seattle, Miami)

**Pros:**
- ✅ **Extremely cheap** (annual plans from $10.88/year)
- ✅ **No-KYC** (privacy-friendly)
- ✅ Good for budget users
- ✅ Black Friday deals year-round

**Cons:**
- ❌ **US only** (no global presence)
- ❌ **Limited RAM** on budget plans
- ❌ **Average network quality**
- ❌ Not suitable for latency-sensitive apps

**TA-DSS Fit:** ⭐⭐ (Too little RAM, US only)

---

### 2.8 Contabo

| Plan | Price | vCPU | RAM | SSD | Traffic |
|------|-------|------|-----|-----|---------|
| **VPS S** | €4.99/month | 4 | 8 GB | 200 GB | 32 TB |
| **VPS M** | €9.99/month | 6 | 16 GB | 400 GB | 32 TB |
| **VPS L** | €17.99/month | 8 | 32 GB | 800 GB | 32 TB |

**Locations:** Germany, US, UK, Singapore, Australia, Japan

**Pros:**
- ✅ **Massive resources** for the price
- ✅ **32 TB traffic** on all plans
- ✅ **Large storage** included
- ✅ Global presence

**Cons:**
- ❌ **Oversold servers** (performance varies)
- ❌ **Average network quality**
- ❌ **High latency** for some regions
- ❌ Not suitable for production-critical apps

**TA-DSS Fit:** ⭐⭐⭐ (Good specs, but reliability concerns)

---

## 3. Mid-Range Providers ($10-30/month)

### 3.1 Alibaba Cloud International

| Plan | Price | vCPU | RAM | SSD | Traffic |
|------|-------|------|-----|-----|---------|
| **1 Core 1GB** | $8.50/month | 1 | 1 GB | 40 GB | 1 TB |
| **2 Core 4GB** | $34/month | 2 | 4 GB | 80 GB | 2 TB |
| **4 Core 8GB** | $68/month | 4 | 8 GB | 160 GB | 4 TB |

**Locations:** 20+ regions (strong in Asia-Pacific: HK, Singapore, Tokyo, Sydney)

**Pros:**
- ✅ **Excellent Asia-Pacific coverage**
- ✅ **Low latency to China** (30-50ms)
- ✅ **No-KYC** for international users
- ✅ **Anonymous payment** (USDT supported)
- ✅ Rich ecosystem (OSS, CDN, RDS)

**Cons:**
- ❌ **More expensive** than Western providers
- ❌ **Complex pricing** (many promotions)
- ❌ UI can be confusing
- ❌ Support quality varies

**TA-DSS Fit:** ⭐⭐⭐⭐ (Best for Asia deployment)

---

### 3.2 AWS Lightsail

| Plan | Price | vCPU | RAM | SSD | Traffic |
|------|-------|------|-----|-----|---------|
| **Basic** | $3.50/month | 1 | 512 MB | 20 GB | 1 TB |
| **Standard** | $5/month | 1 | 1 GB | 40 GB | 2 TB |
| **Mid-Tier** | $10/month | 2 | 2 GB | 60 GB | 3 TB |
| **High-End** | $80/month | 8 | 32 GB | 640 GB | 9 TB |

**Locations:** 15+ regions worldwide

**Pros:**
- ✅ **Fixed monthly pricing** (no surprises)
- ✅ **Integrated with AWS ecosystem**
- ✅ **Simplified management** interface
- ✅ **3 months free** trial available

**Cons:**
- ❌ **Requires credit card** verification
- ❌ **May trigger identity review**
- ❌ **Limited scalability** compared to EC2
- ❌ **No ARM instances** in Lightsail

**TA-DSS Fit:** ⭐⭐⭐ (Good for AWS ecosystem, but limited)

---

### 3.3 Kamatera

| Plan | Price | vCPU | RAM | SSD | Traffic |
|------|-------|------|-----|-----|---------|
| **Custom** | From $4/month | 1-104 | 1-512 GB | 20-1000 GB | 1 TB |

**Locations:** 24 global locations

**Pros:**
- ✅ **Highly customizable** (build your own server)
- ✅ **30-day trial** with $100 credit
- ✅ **Instant provisioning** (within 1 minute)
- ✅ **24/7 support** (phone, email, tickets)
- ✅ 350+ pre-installed apps

**Cons:**
- ❌ **Add-ons can get expensive** (backups, etc.)
- ❌ Must monitor credit usage
- ❌ **Unmanaged** service

**TA-DSS Fit:** ⭐⭐⭐⭐ (Good customization, generous trial)

---

### 3.4 IONOS (1&1)

| Plan | Price | vCPU | RAM | NVMe | Traffic |
|------|-------|------|-----|------|---------|
| **VPS XS** | $2/month (first 6 months) | 1 | 512 MB | 10 GB | Unlimited |
| **VPS S** | $4/month | 1 | 1 GB | 40 GB | Unlimited |
| **VPS M** | $8/month | 2 | 2 GB | 80 GB | Unlimited |
| **VPS L** | $16/month | 4 | 4 GB | 160 GB | Unlimited |

**Locations:** US, UK, Germany, Spain, France

**Pros:**
- ✅ **Cheapest unmanaged VPS** ($2/month intro)
- ✅ **Unlimited traffic** on all plans
- ✅ **Free Plesk** Web Host edition
- ✅ **Mobile app** for server management
- ✅ **No overage fees**

**Cons:**
- ❌ **Price increases** after 6 months
- ❌ **Limited resources** on entry plans
- ❌ **Personal consultant** not always available
- ❌ Requires technical knowledge

**TA-DSS Fit:** ⭐⭐⭐ (Good budget option, but limited RAM)

---

### 3.5 BandwagonHost

| Plan | Price | Type | Features |
|------|-------|------|----------|
| **CN2 GIA-E** | From $169/year | Premium CN2 | Low latency to China |
| **Regular KVM** | From $49/year | Standard | Basic VPS |

**Locations:** US (LA, NYC), HK, Tokyo, Singapore

**Pros:**
- ✅ **CN2 GIA direct connection** to China
- ✅ **Extremely low latency** (30-50ms to China)
- ✅ **No-KYC** (accepts USDT)
- ✅ **No congestion** during peak hours

**Cons:**
- ❌ **Expensive** for the specs
- ❌ **Limited locations**
- ❌ **No monthly billing** (annual only)

**TA-DSS Fit:** ⭐⭐ (Too expensive, limited use case)

---

## 4. Vietnamese Providers

### 4.1 Viettel VPS ⭐ **Best Vietnam Option**

| Plan | Price | vCPU | RAM | SSD | Traffic |
|------|-------|------|-----|-----|---------|
| **Premium 2 Core** | $21.45/month (35% off first year) | 2 | 4 GB | 100 GB | Unlimited |
| **Premium 4 Core** | $33.45/month (35% off first year) | 4 | 8 GB | 200 GB | Unlimited |
| **Premium 8 Core** | $66.45/month (35% off first year) | 8 | 16 GB | 400 GB | Unlimited |

**Locations:** Vietnam (Hanoi, Ho Chi Minh City)

**Pros:**
- ✅ **Military-backed infrastructure** (Viettel is state-owned)
- ✅ **Lowest latency** in Vietnam (<20ms domestic)
- ✅ **Unlimited traffic** on all plans
- ✅ **35% discount** first year
- ✅ **Free snapshot** service (3-year plans)

**Cons:**
- ❌ **More expensive** than international providers
- ❌ **Limited global presence**
- ❌ **Vietnamese language** support primary
- ❌ **KYC required** for Vietnamese users

**TA-DSS Fit:** ⭐⭐⭐⭐ (Best for Vietnam deployment, but pricey)

---

### 4.2 VNPT VPS

| Plan | Price | vCPU | RAM | SSD | Traffic |
|------|-------|------|-----|-----|---------|
| **Business S** | ~$15/month | 2 | 4 GB | 100 GB | Unlimited |
| **Business M** | ~$30/month | 4 | 8 GB | 200 GB | Unlimited |
| **Business L** | ~$60/month | 8 | 16 GB | 400 GB | Unlimited |

**Locations:** Vietnam (nationwide)

**Pros:**
- ✅ **State-owned provider** (reliable)
- ✅ **Nationwide coverage** in Vietnam
- ✅ **Good domestic latency**
- ✅ **Unlimited traffic**

**Cons:**
- ❌ **Higher prices** than international
- ❌ **Limited English** support
- ❌ **Complex pricing** (many promotions)

**TA-DSS Fit:** ⭐⭐⭐ (Good local option, but expensive)

---

### 4.3 IDC Online Vietnam

| Plan | Price | vCPU | RAM | SSD | Traffic |
|------|-------|------|-----|-----|---------|
| **Starter** | ~$10/month | 1 | 2 GB | 50 GB | 2 TB |
| **Business** | ~$25/month | 2 | 4 GB | 100 GB | 5 TB |
| **Enterprise** | ~$50/month | 4 | 8 GB | 200 GB | 10 TB |

**Locations:** Vietnam, Singapore

**Pros:**
- ✅ **Competitive pricing** for Vietnam
- ✅ **Singapore backup** location
- ✅ **Good support** (English available)
- ✅ **Flexible plans**

**Cons:**
- ❌ **Smaller provider** (less established)
- ❌ **Limited data centers**
- ❌ **Variable performance**

**TA-DSS Fit:** ⭐⭐⭐ (Decent local option)

---

### 4.4 CMC Cloud

| Plan | Price | vCPU | RAM | SSD | Traffic |
|------|-------|------|-----|-----|---------|
| **Standard** | ~$20/month | 2 | 4 GB | 100 GB | Unlimited |
| **Premium** | ~$40/month | 4 | 8 GB | 200 GB | Unlimited |

**Locations:** Vietnam, Thailand, Singapore

**Pros:**
- ✅ **Regional presence** (SE Asia)
- ✅ **Good performance**
- ✅ **Unlimited traffic**
- ✅ **Enterprise-grade** infrastructure

**Cons:**
- ❌ **Higher prices**
- ❌ **Limited global** coverage
- ❌ **Complex pricing**

**TA-DSS Fit:** ⭐⭐⭐ (Good for SE Asia, but expensive)

---

### 4.5 VinaHost

| Plan | Price | vCPU | RAM | SSD | Traffic |
|------|-------|------|-----|-----|---------|
| **Vietnam VPS** | From $5/month | 1 | 1 GB | 40 GB | Unlimited |

**Locations:** Vietnam

**Pros:**
- ✅ **Cheapest Vietnam VPS** (from $5/month)
- ✅ **Unlimited traffic**
- ✅ **Free control panel**, SSL, IPv6
- ✅ **99.9% uptime** guarantee

**Cons:**
- ❌ **Limited resources** on budget plans
- ❌ **Average support** quality
- ❌ **Single location**

**TA-DSS Fit:** ⭐⭐⭐ (Budget Vietnam option)

---

## 5. Asian Providers

### 5.1 Tencent Cloud

| Plan | Price | vCPU | RAM | SSD | Traffic |
|------|-------|------|-----|-----|---------|
| **Standard S5** | ~$10/month | 1 | 2 GB | 50 GB | 1 TB |
| **Compute Optimized** | ~$25/month | 2 | 4 GB | 80 GB | 2 TB |

**Locations:** 20+ regions (strong in China, Asia-Pacific)

**Pros:**
- ✅ **Excellent China coverage**
- ✅ **Low latency** to mainland China
- ✅ **Competitive pricing**
- ✅ **Rich ecosystem**

**Cons:**
- ❌ **KYC required** for some services
- ❌ **Complex pricing** structure
- ❌ **Limited English** support

**TA-DSS Fit:** ⭐⭐⭐ (Good for China/Asia, but KYC concerns)

---

### 5.2 Huawei Cloud

| Plan | Price | vCPU | RAM | SSD | Traffic |
|------|-------|------|-----|-----|---------|
| **General Purpose** | ~$15/month | 2 | 4 GB | 80 GB | 2 TB |

**Locations:** 20+ regions (strong in Asia, Africa, Latin America)

**Pros:**
- ✅ **Growing global presence**
- ✅ **Competitive pricing**
- ✅ **Good Asia coverage**
- ✅ **Enterprise-grade** infrastructure

**Cons:**
- ❌ **Geopolitical concerns** (US sanctions)
- ❌ **Limited Western** adoption
- ❌ **Complex pricing**

**TA-DSS Fit:** ⭐⭐ (Geopolitical risks)

---

### 5.3 Linode (Akamai) - Asia

| Plan | Price | vCPU | RAM | SSD | Traffic |
|------|-------|------|-----|-----|---------|
| **Standard** | $10/month | 1 | 2 GB | 50 GB | 2 TB |

**Locations:** Tokyo, Singapore, Mumbai

**Pros:**
- ✅ **Good Asia-Pacific** coverage
- ✅ **Reliable infrastructure**
- ✅ **Excellent support**
- ✅ **Transparent pricing**

**Cons:**
- ❌ **Limited Asian** locations (3 only)
- ❌ **Higher prices** than local providers

**TA-DSS Fit:** ⭐⭐⭐⭐ (Good balance of reliability and coverage)

---

## 6. European Providers

### 6.1 Hetzner ⭐ **Best Europe Value**

Already covered in Budget section - best value for European deployment.

**TA-DSS Fit:** ⭐⭐⭐⭐⭐ (Excellent for Europe)

---

### 6.2 OVHcloud ⭐ **Best Unlimited Traffic**

Already covered in Budget section - unlimited traffic on all plans.

**TA-DSS Fit:** ⭐⭐⭐⭐ (Good for high-traffic scenarios)

---

### 6.3 Scaleway ⭐ **Best European ARM**

| Plan | Price | vCPU | RAM | SSD | Traffic |
|------|-------|------|-----|-----|---------|
| **ARM Instances** | From €5/month | 1 | 2 GB | 50 GB | 500 GB |

**Locations:** France, Netherlands

**Pros:**
- ✅ **ARM instances** available (like Oracle)
- ✅ **European data sovereignty**
- ✅ **GDPR compliant**
- ✅ **Integrated ecosystem**

**Cons:**
- ❌ **Limited locations**
- ❌ **Higher prices** than Hetzner

**TA-DSS Fit:** ⭐⭐⭐⭐ (Good ARM alternative to Oracle)

---

## 7. US Providers

### 7.1 DigitalOcean ⭐ **Best US Developer Experience**

Already covered - excellent documentation and developer tools.

**TA-DSS Fit:** ⭐⭐⭐⭐ (Great for US deployment)

---

### 7.2 Vultr ⭐ **Best US Global Coverage**

Already covered - 32 locations worldwide.

**TA-DSS Fit:** ⭐⭐⭐⭐ (Good global coverage)

---

### 7.3 Linode (Akamai) ⭐ **Best US Long-term Stability**

Already covered - reliable since 2003.

**TA-DSS Fit:** ⭐⭐⭐⭐ (Reliable long-term option)

---

## 8. Recommendations for TA-DSS

### Current Situation

- **Oracle Cloud ARM** capacity unavailable (all ADs full)
- Need **temporary solution** until Oracle available
- Application requires:
  - **24/7 operation** (scheduler must run continuously)
  - **Minimum 2 GB RAM** (ideally 4+ GB)
  - **Persistent storage** (SQLite database)
  - **Python 3.10+** support
  - **Docker** support (preferred)

---

### Temporary Solutions (While Waiting for Oracle)

#### Option 1: Hetzner Cloud CPX11 ⭐ **Recommended Temporary**

| Specification | Value |
|---------------|-------|
| **Price** | €4.99/month (~$5.40/month) |
| **vCPU** | 2 (AMD) |
| **RAM** | 2 GB |
| **SSD** | 40 GB |
| **Traffic** | 20 TB/month |
| **Location** | Germany, Finland, US |

**Why This Option:**
- ✅ **Cheapest viable option** (2 GB RAM minimum)
- ✅ **Reliable infrastructure**
- ✅ **20 TB traffic** (plenty for our needs)
- ✅ **Instant provisioning**
- ✅ **Hourly billing** (can cancel anytime)

**Setup:**
```bash
# Deploy Ubuntu 22.04
# Install Docker
curl -fsSL https://get.docker.com -o get-docker.sh
sudo sh get-docker.sh

# Deploy TA-DSS
cd /opt
git clone <repo> trading-monitor
cd trading-monitor/docker
docker compose up -d --build
```

**Estimated Cost:** €5-10/month (until Oracle available)

---

#### Option 2: Vultr High Frequency $6/month

| Specification | Value |
|---------------|-------|
| **Price** | $6/month |
| **vCPU** | 1 (3.4+ GHz) |
| **RAM** | 1 GB |
| **SSD** | 32 GB |
| **Traffic** | 1 TB/month |
| **Location** | 32 locations worldwide |

**Why This Option:**
- ✅ **Global presence** (choose closest to you)
- ✅ **High frequency CPU** (good performance)
- ✅ **Hourly billing**
- ✅ **One-click Docker** deployment

**Concerns:**
- ⚠️ **Only 1 GB RAM** (may be tight for our app)

**Estimated Cost:** $6-12/month

---

#### Option 3: DigitalOcean (60-Day Trial) ⭐ **Best Trial**

| Specification | Value |
|---------------|-------|
| **Trial Credit** | $200 |
| **Trial Duration** | 60 days |
| **Basic Droplet** | $6/month (1 GB RAM) |
| **Premium Droplet** | $24/month (4 GB RAM) |

**Why This Option:**
- ✅ **60 days free** (longest trial)
- ✅ **$200 credit** (can run 4 GB droplet for 8+ months)
- ✅ **Excellent documentation**
- ✅ **Mature ecosystem**

**Setup:**
- Sign up via GitHub or referral link for $200 credit
- Deploy 4 GB Premium Droplet ($24/month)
- Use credit for 8+ months free

**Estimated Cost:** $0 for 8+ months (with trial credit)

---

### Long-term Solutions (After Oracle)

#### Option A: Oracle Cloud Free Tier ⭐ **Best Long-term**

| Specification | Value |
|---------------|-------|
| **Price** | $0/month |
| **Compute** | 4 OCPU + 24 GB RAM (ARM) |
| **Storage** | 200 GB |
| **Traffic** | Up to 10 TB/month |
| **Duration** | Always Free |

**Action Plan:**
1. **Retry every 2-6 hours** for capacity
2. **Try different regions** (US Ashburn, Phoenix, Frankfurt)
3. **Try different times** (early morning, late evening)
4. **Once available**, deploy immediately

**Estimated Cost:** $0/month (forever)

---

#### Option B: Hetzner Cloud CPX21 ⭐ **Best Paid Alternative**

| Specification | Value |
|---------------|-------|
| **Price** | €9.99/month (~$10.80/month) |
| **vCPU** | 3 (AMD) |
| **RAM** | 4 GB |
| **SSD** | 80 GB |
| **Traffic** | 24 TB/month |
| **Location** | Germany, Finland, US |

**Why This Option:**
- ✅ **Excellent value** (4 GB RAM for €10)
- ✅ **Reliable infrastructure**
- ✅ **24 TB traffic**
- ✅ **No contract** (cancel anytime)

**Estimated Cost:** €10/month (~$130/year)

---

#### Option C: OVHcloud VPS-2 ⭐ **Best Unlimited Traffic**

| Specification | Value |
|---------------|-------|
| **Price** | $8.40/month |
| **vCPU** | 2 |
| **RAM** | 4 GB |
| **SSD** | 40 GB |
| **Traffic** | **Unlimited** |
| **Location** | 19 locations worldwide |

**Why This Option:**
- ✅ **Unlimited traffic** (no overage concerns)
- ✅ **Affordable** (4 GB for $8.40)
- ✅ **DDoS protection** included

**Estimated Cost:** $8.40/month (~$100/year)

---

## Comparison Table: All Options for TA-DSS

| Provider | Plan | Price | vCPU | RAM | Traffic | TA-DSS Fit | Notes |
|----------|------|-------|------|-----|---------|------------|-------|
| **Oracle Cloud** | Always Free | $0/mo | 4 | 24 GB | 10 TB | ⭐⭐⭐⭐⭐ | **Target** (capacity issue) |
| **Hetzner** | CPX11 | €5/mo | 2 | 2 GB | 20 TB | ⭐⭐⭐⭐⭐ | **Best temporary** |
| **Hetzner** | CPX21 | €10/mo | 3 | 4 GB | 24 TB | ⭐⭐⭐⭐⭐ | **Best paid** |
| **DigitalOcean** | 60-day trial | $0/mo* | 2 | 4 GB | 4 TB | ⭐⭐⭐⭐⭐ | **Best trial** |
| **OVHcloud** | VPS-2 | $8.40/mo | 2 | 4 GB | Unlimited | ⭐⭐⭐⭐ | Unlimited traffic |
| **Vultr** | HF $6 | $6/mo | 1 | 1 GB | 1 TB | ⭐⭐⭐ | Tight on RAM |
| **Alibaba Cloud** | 2 Core 4GB | $34/mo | 2 | 4 GB | 2 TB | ⭐⭐⭐⭐ | Best for Asia |
| **Viettel** | Premium 2C | $21/mo | 2 | 4 GB | Unlimited | ⭐⭐⭐⭐ | Best Vietnam |
| **Scaleway** | ARM | €5/mo | 1 | 2 GB | 500 GB | ⭐⭐⭐⭐ | ARM alternative |
| **Linode** | Standard | $10/mo | 1 | 2 GB | 2 TB | ⭐⭐⭐⭐ | Reliable |
| **Contabo** | VPS S | €5/mo | 4 | 8 GB | 32 TB | ⭐⭐⭐ | Oversold concerns |
| **AWS Lightsail** | $10 plan | $10/mo | 2 | 2 GB | 3 TB | ⭐⭐⭐ | 3 months free |
| **Azure** | B1s | ~$9.50/mo | 1 | 1 GB | 15 GB | ⭐⭐ | 12 months free |
| **GCP** | e2-micro | $6.50/mo | 1 | 0.6 GB | 1 GB | ⭐ | Too little RAM |
| **Render** | Free | $0/mo | 0.1 | 512 MB | 100 GB | ⭐ | Sleeps, too little |

---

## Final Recommendations

### Immediate Action (This Week)

1. **Retry Oracle Cloud every 2-6 hours**
   - Try **US Ashburn**, **Phoenix**, **Frankfurt** regions
   - Try **early morning** (2-6 AM local time)
   - Try **late evening** (10 PM - 2 AM local time)

2. **If Oracle still unavailable, deploy to Hetzner CPX11**
   - Cost: €5/month
   - Setup time: 30 minutes
   - Can cancel anytime when Oracle available

3. **Alternative: Use DigitalOcean 60-day trial**
   - $200 credit = 8+ months free (4 GB droplet)
   - Best for testing while waiting for Oracle

### Medium-term (1-3 Months)

1. **If Oracle becomes available:** Migrate immediately
2. **If Oracle still unavailable:**
   - Upgrade to **Hetzner CPX21** (€10/month, 4 GB RAM)
   - Or stay on **DigitalOcean** using trial credit

### Long-term (3+ Months)

1. **Primary:** Oracle Cloud Free Tier (if available)
2. **Secondary:** Hetzner CPX21 (€10/month)
3. **Tertiary:** OVHcloud VPS-2 ($8.40/month, unlimited traffic)

---

## Migration Path

```
Now (Week 1)
├─ Retry Oracle Cloud (every 2-6 hours)
└─ If unavailable → Deploy to Hetzner CPX11 (€5/month)

Month 1-2
├─ Continue retrying Oracle
├─ If Oracle available → Migrate
└─ If Oracle unavailable → Upgrade to Hetzner CPX21 (€10/month)

Month 3+
├─ Oracle available → Migrate to Oracle ($0/month)
└─ Oracle unavailable → Stay on Hetzner CPX21 or OVHcloud VPS-2
```

---

## Cost Summary

| Scenario | Monthly Cost | Annual Cost |
|----------|--------------|-------------|
| **Oracle Cloud (Target)** | $0 | $0 |
| **Hetzner CPX11 (Temporary)** | €5 (~$5.40) | €60 (~$65) |
| **Hetzner CPX21 (Paid Alternative)** | €10 (~$10.80) | €120 (~$130) |
| **DigitalOcean (Trial)** | $0 (8 months) | $0 (8 months) |
| **OVHcloud VPS-2** | $8.40 | $100 |
| **Vultr HF $6** | $6 | $72 |

---

## Conclusion

**Best Overall Strategy:**

1. **Keep trying Oracle Cloud** (best free tier, worth the wait)
2. **Use Hetzner CPX11 as temporary** (€5/month, can cancel anytime)
3. **Migrate to Oracle when available** (save €60/year)

**If Oracle never becomes available:**

- **Best value:** Hetzner CPX21 (€10/month, 4 GB RAM)
- **Best unlimited traffic:** OVHcloud VPS-2 ($8.40/month)
- **Best Asia:** Alibaba Cloud 2 Core 4GB ($34/month)
- **Best Vietnam:** Viettel Premium 2 Core ($21.45/month first year)

---

**Report Generated:** March 3, 2026  
**Next Review:** After Oracle capacity check (2-6 hours)  
**Contact:** [Your contact info]
