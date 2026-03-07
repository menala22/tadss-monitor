# Security Check Skill - Credentials Scanner

**Purpose:** Automatically scan files for exposed credentials, API keys, and sensitive information before committing to git or sharing documents.

**Trigger:** Use this skill when:
- Creating documentation files (.md, .txt, .rst)
- Before git commits
- When reviewing code changes
- When preparing files for public sharing

---

## What This Skill Checks

### 1. IP Addresses
- **IPv4:** `XXX.XXX.XXX.XXX` patterns (except localhost `127.0.0.1`)
- **Risk:** Exposes infrastructure location

### 2. API Keys & Tokens
- **Telegram Bot Tokens:** Pattern like `1234567890:ABCdefGHIjklMNOpqrsTUVwxyz`
- **Generic API Keys:** Long alphanumeric strings
- **Bearer Tokens:** `Bearer [token]` patterns
- **Risk:** Unauthorized API access

### 3. Database Credentials
- **Connection Strings:** `postgresql://user:password@host`
- **Passwords in URLs:** `://user:pass@`
- **Risk:** Database compromise

### 4. Private Keys
- **SSH Keys:** `-----BEGIN RSA PRIVATE KEY-----`
- **AWS Keys:** `AKIA[0-9A-Z]{16}`
- **Risk:** System access compromise

### 5. Personal Information
- **Chat IDs:** Numeric IDs like `652745650`
- **Email Addresses:** `user@domain.com` (context-dependent)
- **Phone Numbers:** Various formats
- **Risk:** Privacy violation, targeted attacks

### 6. Cloud Provider Secrets
- **AWS Secret Keys:** 40-character base64 strings
- **Google Cloud Keys:** JSON key patterns
- **Azure Connection Strings:** `DefaultEndpointsProtocol=`
- **Risk:** Cloud infrastructure compromise

---

## How to Use

### Method 1: Manual Scan

```bash
# Scan a specific file
python scripts/security_check.py <filename>

# Scan all markdown files
python scripts/security_check.py "**/*.md"

# Scan before commit
python scripts/security_check.py --staged
```

### Method 2: Using This Skill

Simply invoke the `security-check` skill:

```
skill: "security-check"
```

This will automatically:
- Scan staged git files
- Scan recent documentation changes
- Report any exposed credentials
- Provide remediation steps

### Method 3: Pre-commit Hook

Add to `.git/hooks/pre-commit`:

```bash
#!/bin/bash
# Pre-commit security check

echo "🔒 Running security check..."
python scripts/security_check.py --staged

if [ $? -ne 0 ]; then
    echo "❌ Security check failed! Remove credentials before committing."
    exit 1
fi

echo "✅ Security check passed"
```

### Method 3: CI/CD Pipeline

Add to GitHub Actions (`.github/workflows/security-check.yml`):

```yaml
name: Security Check

on: [push, pull_request]

jobs:
  security-scan:
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v3
      
      - name: Run Security Check
        run: |
          python scripts/security_check.py "**/*.md" "**/*.py" "**/*.yml"
```

---

## Patterns to Detect

### Regular Expressions

```python
# IPv4 Address (excluding localhost)
IPV4_PATTERN = r'\b(?:(?:25[0-5]|2[0-4][0-9]|[01]?[0-9][0-9]?)\.){3}(?:25[0-5]|2[0-4][0-9]|[01]?[0-9][0-9]?)\b'

# Telegram Bot Token
TELEGRAM_BOT_TOKEN = r'\b\d{9,10}:[0-9A-Za-z_-]{35}\b'

# Generic API Key (32+ alphanumeric)
API_KEY_PATTERN = r'\b[A-Za-z0-9]{32,}\b'

# Password in URL
PASSWORD_IN_URL = r'://[^:]+:[^@]+@'

# AWS Access Key ID
AWS_ACCESS_KEY = r'AKIA[0-9A-Z]{16}'

# AWS Secret Access Key
AWS_SECRET_KEY = r'[A-Za-z0-9/+=]{40}'

# Private Key Header
PRIVATE_KEY = r'-----BEGIN (RSA |EC |DSA )?PRIVATE KEY-----'

# Google Cloud API Key
GOOGLE_API_KEY = r'AIza[0-9A-Za-z_-]{35}'

# Generic Secret/Token
SECRET_PATTERN = r'(?i)(secret|token|api_key|apikey|password|passwd|pwd)\s*[=:]\s*["\']?[A-Za-z0-9_-]{16,}["\']?'
```

---

## Example Output

### Clean File
```
✅ Security Check Passed

Files scanned: 1
Issues found: 0

Status: Safe to commit/share
```

### File with Credentials
```
❌ Security Check Failed

Files scanned: 1
Issues found: 3

🔴 HIGH RISK: DASHBOARD_DOCUMENTATION.md
   Line 530: Telegram Bot Token detected
   Pattern: 8726527766:AAF8F9P3ES6t...
   Recommendation: Replace with placeholder

🔴 HIGH RISK: DASHBOARD_DOCUMENTATION.md
   Line 531: Telegram Chat ID detected
   Pattern: 652745650
   Recommendation: Replace with placeholder

🟡 MEDIUM RISK: DASHBOARD_DOCUMENTATION.md
   Line 520: Public IP Address detected
   Pattern: 35.188.118.182
   Recommendation: Use VM_EXTERNAL_IP placeholder

Status: DO NOT COMMIT - Remove credentials first
```

---

## Allowed Exceptions

Some patterns are safe and should be ignored:

| Pattern | Reason | Example |
|---------|--------|---------|
| `127.0.0.1` | Localhost | Always safe |
| `0.0.0.0` | Bind all interfaces | Configuration only |
| `XX.XXX.XXX.XXX` | Documentation placeholders | `VM_EXTERNAL_IP` |
| `your_token_here` | Explicit placeholders | Safe by design |
| `REDACTED` | Already masked | Safe |
| `[REMOVED]` | Already removed | Safe |
| Test/Dummy values | Obviously fake | `test_key_12345` |

---

## Remediation Guide

### If Credentials Found

1. **Replace with Placeholder**
   ```markdown
   # Before
   API_KEY=sk_live_1234567890abcdef
   
   # After
   API_KEY=your_api_key_here
   ```

2. **Use Environment Variable Reference**
   ```markdown
   # Before
   Connect to: postgresql://admin:password123@192.168.1.100/db
   
   # After
   Connect to: `postgresql://${DB_USER}:${DB_PASSWORD}@${DB_HOST}/${DB_NAME}`
   ```

3. **Reference External Configuration**
   ```markdown
   # Before
   VM IP: 35.188.118.182
   
   # After
   VM IP: See `.env` file for `VM_EXTERNAL_IP`
   ```

### If Already Committed

1. **Revoke the Credential Immediately**
   - Change passwords
   - Regenerate API keys
   - Rotate tokens

2. **Remove from Git History**
   ```bash
   # If recent commit
   git reset --soft HEAD~1
   # Remove credentials, then recommit
   
   # If old commit, use BFG Repo-Cleaner
   java -jar bfg.jar --replace-text passwords.txt repo.git
   ```

3. **Force Push Cleaned History**
   ```bash
   git push --force --no-verify
   ```

---

## Integration with Other Tools

### GitLeaks (Advanced Scanning)

```bash
# Install
brew install gitleaks

# Scan repository
gitleaks detect --source . --verbose

# Scan staged changes
gitleaks protect --source . --staged
```

### TruffleHog

```bash
# Install
pip install truffleHog

# Scan repository
trufflehog --regex --entropy=False .
```

### Pre-commit Framework

```yaml
# .pre-commit-config.yaml
repos:
  - repo: https://github.com/Yelp/detect-secrets
    rev: v1.4.0
    hooks:
      - id: detect-secrets
        args: ['--baseline', '.secrets.baseline']
```

---

## Best Practices

### DO ✅
- Use environment variables for all secrets
- Add `.env` to `.gitignore`
- Use placeholder values in documentation
- Run security check before every commit
- Rotate credentials periodically
- Use secret management tools (Vault, AWS Secrets Manager)

### DON'T ❌
- Hardcode credentials in code
- Commit `.env` files
- Share API keys in documentation
- Use production credentials in development
- Store passwords in plain text
- Ignore security check warnings

---

## Files to Always Exclude from Git

```gitignore
# Environment variables
.env
.env.local
.env.production
.env.*.local

# Credentials
*.pem
*.key
*.p12
*.pfx
credentials.json
service-account.json

# IDE secrets
.idea/workspace.xml
.vscode/settings.json

# Logs (may contain sensitive data)
*.log
logs/

# Database files
*.db
*.sqlite
data/
```

---

## Quick Reference Card

| Check | Command | Frequency |
|-------|---------|-----------|
| **Scan file** | `python scripts/security_check.py file.md` | Before sharing |
| **Scan staged** | `python scripts/security_check.py --staged` | Before commit |
| **Scan repo** | `python scripts/security_check.py "**/*"` | Weekly |
| **Git history** | `gitleaks detect --source .` | Monthly |
| **Rotate keys** | Manual (via provider) | Quarterly |

---

## Contact & Escalation

If you accidentally commit credentials:

1. **IMMEDIATE:** Revoke the credential
2. **WITHIN 1 HOUR:** Rotate all related credentials
3. **WITHIN 24 HOURS:** Review access logs for suspicious activity
4. **WITHIN 48 HOURS:** Document incident and update security procedures

---

## Appendix: Complete Security Check Script

**Location:** `scripts/security_check.py`

**Note:** If the script is lost or deleted, recreate it using the code below:

```python
#!/usr/bin/env python3
"""
TA-DSS Security Check - Credentials Scanner

Scans files for exposed credentials, API keys, and sensitive information.

Usage:
    python scripts/security_check.py <file_or_pattern>
    python scripts/security_check.py --staged
    python scripts/security_check.py "**/*.md"

Examples:
    python scripts/security_check.py README.md
    python scripts/security_check.py --staged
    python scripts/security_check.py "**/*.md" "**/*.py"
"""

import argparse
import glob
import os
import re
import subprocess
import sys
from pathlib import Path
from typing import Dict, List, Tuple

# Color codes for terminal output
class Colors:
    RED = '\033[91m'
    GREEN = '\033[92m'
    YELLOW = '\033[93m'
    BLUE = '\033[94m'
    MAGENTA = '\033[95m'
    CYAN = '\033[96m'
    RESET = '\033[0m'
    BOLD = '\033[1m'

# Security patterns to detect
SECURITY_PATTERNS = {
    # High Risk - Should never be in code/docs
    'telegram_bot_token': {
        'pattern': r'\b\d{9,10}:[0-9A-Za-z_-]{35}\b',
        'risk': 'HIGH',
        'color': Colors.RED,
        'message': 'Telegram Bot Token detected',
        'recommendation': 'Replace with placeholder: your_bot_token_here'
    },

    'password_in_url': {
        'pattern': r'://[^:]+:[^@]+@',
        'risk': 'HIGH',
        'color': Colors.RED,
        'message': 'Password in URL detected',
        'recommendation': 'Use environment variables: ${DB_PASSWORD}'
    },

    'private_key': {
        'pattern': r'-----BEGIN (RSA |EC |DSA )?PRIVATE KEY-----',
        'risk': 'CRITICAL',
        'color': Colors.RED,
        'message': 'Private Key detected',
        'recommendation': 'Never commit private keys. Use SSH key management.'
    },

    'aws_access_key': {
        'pattern': r'AKIA[0-9A-Z]{16}',
        'risk': 'CRITICAL',
        'color': Colors.RED,
        'message': 'AWS Access Key ID detected',
        'recommendation': 'Use IAM roles or environment variables'
    },

    'aws_secret_key': {
        'pattern': r'(?<![A-Za-z0-9/+=])[A-Za-z0-9/+=]{40}(?![A-Za-z0-9/+=])',
        'risk': 'HIGH',
        'color': Colors.RED,
        'message': 'Possible AWS Secret Access Key detected',
        'recommendation': 'Use environment variables for secrets',
        'min_length': 40,
        'exceptions': ['========================================']
    },

    # Medium Risk - Should be externalized
    'ipv4_address': {
        'pattern': r'\b(?:(?:25[0-5]|2[0-4][0-9]|[01]?[0-9][0-9]?)\.){3}(?:25[0-5]|2[0-4][0-9]|[01]?[0-9][0-9]?)\b',
        'risk': 'MEDIUM',
        'color': Colors.YELLOW,
        'message': 'Public IP Address detected',
        'recommendation': 'Use placeholder: VM_EXTERNAL_IP or ${VM_IP}',
        'exceptions': ['127.0.0.1', '0.0.0.0', '255.255.255.255']
    },

    'generic_api_key': {
        'pattern': r'(?i)(api_key|apikey|api-key)\s*[=:]\s*["\']?[A-Za-z0-9_-]{20,}["\']?',
        'risk': 'HIGH',
        'color': Colors.RED,
        'message': 'Generic API Key detected',
        'recommendation': 'Use environment variables: ${API_KEY}'
    },

    'generic_secret': {
        'pattern': r'(?i)(secret|token|password|passwd|pwd)\s*[=:]\s*["\']?[A-Za-z0-9_-]{16,}["\']?',
        'risk': 'HIGH',
        'color': Colors.RED,
        'message': 'Generic Secret/Token detected',
        'recommendation': 'Use environment variables for secrets'
    },

    'google_api_key': {
        'pattern': r'AIza[0-9A-Za-z_-]{35}',
        'risk': 'HIGH',
        'color': Colors.RED,
        'message': 'Google Cloud API Key detected',
        'recommendation': 'Use environment variables or GCP Secret Manager'
    },

    'github_token': {
        'pattern': r'gh[pousr]_[A-Za-z0-9_]{36,}',
        'risk': 'HIGH',
        'color': Colors.RED,
        'message': 'GitHub Token detected',
        'recommendation': 'Use environment variables for tokens'
    },

    'chat_id': {
        'pattern': r'\b\d{9,10}\b',
        'risk': 'MEDIUM',
        'color': Colors.YELLOW,
        'message': 'Possible Chat ID or Phone Number detected',
        'recommendation': 'Replace with placeholder: your_chat_id_here',
        'context_required': True
    },
}

# Safe patterns to ignore
SAFE_PATTERNS = [
    r'your_.*_here',
    r'\[.*\]',
    r'\$\{.*\}',
    r'VM_EXTERNAL_IP',
    r'localhost',
    r'127\.0\.0\.1',
    r'0\.0\.0\.0',
    r'255\.255\.255\.255',
    r'REDACTED',
    r'REMOVED',
    r'MASKED',
    r'example\.com',
    r'test_',
    r'dummy_',
    r'^=+$',
    r'your_bot_token_here',
    r'your_chat_id_here',
    r'your_.*',
    r'^\s*#',
]


def is_safe_pattern(line: str, match: str, pattern_name: str) -> bool:
    """Check if the match is a known safe pattern."""
    for safe in SAFE_PATTERNS:
        if re.search(safe, match, re.IGNORECASE):
            return True

    if 'placeholder' in line.lower() or 'masked' in line.lower() or 'security' in line.lower():
        return True

    if pattern_name in SECURITY_PATTERNS:
        exceptions = SECURITY_PATTERNS[pattern_name].get('exceptions', [])
        if match in exceptions:
            return True

    return False


def is_contextual_match(lines: List[str], line_num: int, pattern_name: str) -> bool:
    """Check if the match has appropriate context (for contextual patterns)."""
    if pattern_name != 'chat_id':
        return True

    context_window = max(0, line_num - 3), min(len(lines), line_num + 3)
    context = '\n'.join(lines[context_window[0]:context_window[1]])

    telegram_keywords = ['telegram', 'bot', 'chat', 'chat_id', 'user_id']
    return any(keyword in context.lower() for keyword in telegram_keywords)


def scan_file(filepath: str) -> List[Dict]:
    """Scan a single file for security issues."""
    issues = []

    try:
        with open(filepath, 'r', encoding='utf-8', errors='ignore') as f:
            content = f.read()
            lines = content.split('\n')
    except Exception as e:
        return [{
            'line': 0,
            'pattern': 'ERROR',
            'risk': 'ERROR',
            'color': Colors.MAGENTA,
            'message': f'Could not read file: {e}',
            'recommendation': 'Check file permissions'
        }]

    for line_num, line in enumerate(lines, 1):
        for pattern_name, pattern_info in SECURITY_PATTERNS.items():
            matches = re.finditer(pattern_info['pattern'], line)

            for match in matches:
                matched_text = match.group()

                if is_safe_pattern(line, matched_text, pattern_name):
                    continue

                exceptions = pattern_info.get('exceptions', [])
                if matched_text in exceptions:
                    continue

                if not is_contextual_match(lines, line_num, pattern_name):
                    continue

                if pattern_name in ['generic_secret', 'generic_api_key'] and len(matched_text) < 25:
                    continue

                issues.append({
                    'line': line_num,
                    'pattern': pattern_name,
                    'risk': pattern_info['risk'],
                    'color': pattern_info['color'],
                    'message': pattern_info['message'],
                    'matched_text': matched_text[:50] + ('...' if len(matched_text) > 50 else ''),
                    'recommendation': pattern_info['recommendation']
                })

    return issues


def get_staged_files() -> List[str]:
    """Get list of staged files from git."""
    try:
        result = subprocess.run(
            ['git', 'diff', '--cached', '--name-only', '--diff-filter=ACM'],
            capture_output=True,
            text=True,
            check=True
        )
        return result.stdout.strip().split('\n') if result.stdout.strip() else []
    except subprocess.CalledProcessError:
        return []


def scan_files(file_patterns: List[str]) -> Tuple[int, int, Dict[str, List[Dict]]]:
    """Scan multiple files matching patterns."""
    total_files = 0
    total_issues = 0
    all_issues = {}

    for pattern in file_patterns:
        files = glob.glob(pattern, recursive=True)

        for filepath in files:
            if any(filepath.endswith(ext) for ext in ['.pyc', '.pyo', '.so', '.dll', '.exe', '.bin']):
                continue

            if any(skip in filepath for skip in ['node_modules/', 'venv/', '__pycache__/', '.git/', 'build/', 'dist/']):
                continue

            total_files += 1
            issues = scan_file(filepath)

            if issues:
                all_issues[filepath] = issues
                total_issues += len(issues)

    return total_files, total_issues, all_issues


def print_report(total_files: int, total_issues: int, all_issues: Dict[str, List[Dict]]) -> int:
    """Print security scan report."""
    print(f"\n{Colors.BOLD}{'='*70}{Colors.RESET}")
    print(f"{Colors.BOLD}🔒 TA-DSS Security Check Report{Colors.RESET}")
    print(f"{Colors.BOLD}{'='*70}{Colors.RESET}\n")

    print(f"Files scanned: {total_files}")
    print(f"Issues found: {total_issues}\n")

    if not all_issues:
        print(f"{Colors.GREEN}✅ Security Check Passed{Colors.RESET}")
        print(f"\n{Colors.GREEN}Status: Safe to commit/share{Colors.RESET}\n")
        return 0

    high_risk = []
    medium_risk = []

    for filepath, issues in all_issues.items():
        for issue in issues:
            if issue['risk'] in ['HIGH', 'CRITICAL']:
                high_risk.append((filepath, issue))
            else:
                medium_risk.append((filepath, issue))

    if high_risk:
        print(f"{Colors.RED}{Colors.BOLD}🔴 HIGH RISK ISSUES{Colors.RESET}\n")

        current_file = None
        for filepath, issue in high_risk:
            if filepath != current_file:
                print(f"{Colors.MAGENTA}File: {filepath}{Colors.RESET}")
                current_file = filepath

            print(f"  {Colors.RED}Line {issue['line']}: {issue['message']}{Colors.RESET}")
            print(f"    Match: {issue['matched_text']}")
            print(f"    💡 Recommendation: {issue['recommendation']}\n")

    if medium_risk:
        print(f"{Colors.YELLOW}{Colors.BOLD}🟡 MEDIUM RISK ISSUES{Colors.RESET}\n")

        current_file = None
        for filepath, issue in medium_risk:
            if filepath != current_file:
                print(f"{Colors.MAGENTA}File: {filepath}{Colors.RESET}")
                current_file = filepath

            print(f"  {Colors.YELLOW}Line {issue['line']}: {issue['message']}{Colors.RESET}")
            print(f"    Match: {issue['matched_text']}")
            print(f"    💡 Recommendation: {issue['recommendation']}\n")

    print(f"{Colors.BOLD}{'='*70}{Colors.RESET}")

    if high_risk:
        print(f"\n{Colors.RED}{Colors.BOLD}❌ Security Check FAILED{Colors.RESET}")
        print(f"\n{Colors.RED}{Colors.BOLD}Status: DO NOT COMMIT - Remove credentials first!{Colors.RESET}\n")
        print(f"{Colors.YELLOW}Next steps:{Colors.RESET}")
        print(f"  1. Replace all detected credentials with placeholders")
        print(f"  2. If already committed, revoke and rotate the credentials immediately")
        print(f"  3. Re-run security check to verify all issues are resolved\n")
        return 1
    else:
        print(f"\n{Colors.YELLOW}⚠️  Security Check Passed with Warnings{Colors.RESET}")
        print(f"\n{Colors.YELLOW}Status: Review medium risk issues before committing{Colors.RESET}\n")
        return 0


def main():
    parser = argparse.ArgumentParser(
        description='TA-DSS Security Check - Scan for exposed credentials',
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  python scripts/security_check.py README.md
  python scripts/security_check.py --staged
  python scripts/security_check.py "**/*.md" "**/*.py"
  python scripts/security_check.py docs/ --recursive
        """
    )

    parser.add_argument('files', nargs='*', help='Files or glob patterns to scan')
    parser.add_argument('--staged', action='store_true', help='Scan staged git files')
    parser.add_argument('-r', '--recursive', action='store_true', help='Scan directories recursively')

    args = parser.parse_args()

    file_patterns = []

    if args.staged:
        staged_files = get_staged_files()
        if staged_files:
            file_patterns.extend(staged_files)
        else:
            print(f"{Colors.YELLOW}No staged files found{Colors.RESET}")
            return 0

    if args.files:
        file_patterns.extend(args.files)

    if not file_patterns:
        file_patterns = ['**/*.md', '**/*.rst', '**/*.txt']
        if not args.recursive:
            file_patterns = ['*.md', '*.rst', '*.txt']

    if args.recursive and not any('/**/' in p for p in file_patterns):
        file_patterns = [f'**/{p}' if not p.startswith('**/') else p for p in file_patterns]

    print(f"{Colors.CYAN}Scanning files...{Colors.RESET}\n")
    total_files, total_issues, all_issues = scan_files(file_patterns)

    exit_code = print_report(total_files, total_issues, all_issues)

    return exit_code


if __name__ == '__main__':
    sys.exit(main())
```

---

**Skill Version:** 1.0.0
**Last Updated:** March 5, 2026
**Maintained By:** Security Team
