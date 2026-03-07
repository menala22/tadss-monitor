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
        'min_length': 40,  # Must be exactly 40 chars
        'exceptions': ['========================================']  # Separator lines
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
        'context_required': True  # Only flag if near Telegram context
    },
}

# Safe patterns to ignore
SAFE_PATTERNS = [
    r'your_.*_here',  # Explicit placeholders
    r'\[.*\]',  # Bracketed placeholders
    r'\$\{.*\}',  # Environment variable references
    r'VM_EXTERNAL_IP',  # Our documented placeholder
    r'localhost',  # Local development
    r'127\.0\.0\.1',  # Localhost IP
    r'0\.0\.0\.0',  # Bind all interfaces
    r'255\.255\.255\.255',  # Broadcast
    r'REDACTED',  # Already masked
    r'REMOVED',  # Already removed
    r'MASKED',  # Already masked
    r'example\.com',  # Example domain
    r'test_',  # Test values
    r'dummy_',  # Dummy values
    r'^=+$',  # Separator lines (====)
    r'your_bot_token_here',  # Our placeholder
    r'your_chat_id_here',  # Our placeholder
    r'your_.*',  # Any your_* placeholder
    r'^\s*#',  # Comment lines
]


def is_safe_pattern(line: str, match: str, pattern_name: str) -> bool:
    """Check if the match is a known safe pattern."""
    # Check safe patterns list
    for safe in SAFE_PATTERNS:
        if re.search(safe, match, re.IGNORECASE):
            return True
    
    # Check if it's in a comment about security
    if 'placeholder' in line.lower() or 'masked' in line.lower() or 'security' in line.lower():
        return True
    
    # Check pattern-specific exceptions
    if pattern_name in SECURITY_PATTERNS:
        exceptions = SECURITY_PATTERNS[pattern_name].get('exceptions', [])
        if match in exceptions:
            return True
    
    return False


def is_contextual_match(lines: List[str], line_num: int, pattern_name: str) -> bool:
    """Check if the match has appropriate context (for contextual patterns)."""
    if pattern_name != 'chat_id':
        return True  # Non-contextual patterns always match
    
    # For chat_id, check if near Telegram-related keywords
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

                # Skip if it's a safe pattern
                if is_safe_pattern(line, matched_text, pattern_name):
                    continue

                # Skip if it's an exception (like localhost for IP)
                exceptions = pattern_info.get('exceptions', [])
                if matched_text in exceptions:
                    continue
                
                # Skip if contextual pattern lacks context
                if not is_contextual_match(lines, line_num, pattern_name):
                    continue
                
                # Skip very short matches for generic patterns
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
            # Skip common non-text files
            if any(filepath.endswith(ext) for ext in ['.pyc', '.pyo', '.so', '.dll', '.exe', '.bin']):
                continue
            
            # Skip files in common build/vendor directories
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
    
    # Group by risk level
    high_risk = []
    medium_risk = []
    
    for filepath, issues in all_issues.items():
        for issue in issues:
            if issue['risk'] in ['HIGH', 'CRITICAL']:
                high_risk.append((filepath, issue))
            else:
                medium_risk.append((filepath, issue))
    
    # Print high risk issues first
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
    
    # Print medium risk issues
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
    
    # Print summary
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
    
    parser.add_argument(
        'files',
        nargs='*',
        help='Files or glob patterns to scan'
    )
    
    parser.add_argument(
        '--staged',
        action='store_true',
        help='Scan staged git files'
    )
    
    parser.add_argument(
        '-r', '--recursive',
        action='store_true',
        help='Scan directories recursively'
    )
    
    args = parser.parse_args()
    
    # Determine files to scan
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
        # Default: scan common documentation files
        file_patterns = ['**/*.md', '**/*.rst', '**/*.txt']
        if not args.recursive:
            file_patterns = ['*.md', '*.rst', '*.txt']
    
    # Add recursive patterns if requested
    if args.recursive and not any('/**/' in p for p in file_patterns):
        file_patterns = [f'**/{p}' if not p.startswith('**/') else p for p in file_patterns]
    
    # Scan files
    print(f"{Colors.CYAN}Scanning files...{Colors.RESET}\n")
    total_files, total_issues, all_issues = scan_files(file_patterns)
    
    # Print report
    exit_code = print_report(total_files, total_issues, all_issues)
    
    return exit_code


if __name__ == '__main__':
    sys.exit(main())
