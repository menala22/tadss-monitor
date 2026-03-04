# Security Checklist: Handling Secrets with AI Coding Assistants

## ⚠️ Critical Rules

| Rule | Status | Notes |
|------|--------|-------|
| Never commit `.env` file | ☐ | Already in `.gitignore` |
| Never paste real secrets in chat | ☐ | AI conversations may be logged/stored |
| Use placeholders when sharing code | ☐ | `your_token_here` not `sk-abc123...` |
| Rotate exposed secrets immediately | ☐ | If leaked, regenerate ASAP |

---

## Pre-Development Checklist

### 1. Environment Setup
- [ ] Copy `.env.example` to `.env`
- [ ] Fill in real values **locally only**
- [ ] Verify `.env` is in `.gitignore`
- [ ] Set restrictive file permissions: `chmod 600 .env`

### 2. Git Configuration
```bash
# Verify .env is ignored
git check-ignore .env

# If accidentally committed, remove from history
git rm --cached .env
git commit -m "Remove .env from tracking"
```

### 3. Secret Generation
```bash
# Generate secure SECRET_KEY
openssl rand -hex 32

# Generate Telegram Bot Token (via @BotFather)
# Follow @BotFather instructions in Telegram

# Find your Chat ID (via @userinfobot)
# Message the bot and note your ID
```

---

## During AI-Assisted Development

### ✅ Safe to Share with AI
```python
# Configuration structure
class Settings(BaseSettings):
    telegram_bot_token: str
    telegram_chat_id: str
    database_url: str
```

```python
# Error handling patterns
try:
    await bot.send_message(chat_id, message)
except TelegramError as e:
    logger.error(f"Telegram error: {e}")
```

### ❌ NEVER Share with AI
```
✗ TELEGRAM_BOT_TOKEN=1234567890:ABCdefGHIjklMNOpqrsTUVwxyz
✗ API_KEY=sk-proj-abc123xyz789
✗ AWS_SECRET_ACCESS_KEY=wJalrXUtnFEMI/K7MDENG/bPxRfiCYEXAMPLEKEY
```

### ✅ Use Placeholders Instead
```
✓ TELEGRAM_BOT_TOKEN=your_bot_token_here
✓ API_KEY=<your_api_key>
✓ SECRET_KEY=${SECRET_KEY}
```

---

## Code Security Patterns

### 1. Load Secrets Safely
```python
# src/config.py
from pydantic_settings import BaseSettings
from typing import Optional

class Settings(BaseSettings):
    """Application settings loaded from environment variables."""
    
    telegram_bot_token: Optional[str] = None
    telegram_chat_id: Optional[str] = None
    database_url: str = "sqlite:///./positions.db"
    secret_key: str = "dev-secret-key-change-in-prod"
    
    class Config:
        env_file = ".env"
        env_file_encoding = "utf-8"

settings = Settings()
```

### 2. Validate Required Secrets
```python
def validate_telegram_config() -> bool:
    """Validate Telegram configuration is present."""
    if not settings.telegram_bot_token:
        logger.error("TELEGRAM_BOT_TOKEN not configured")
        return False
    if not settings.telegram_chat_id:
        logger.error("TELEGRAM_CHAT_ID not configured")
        return False
    return True
```

### 3. Mask Secrets in Logs
```python
def mask_token(token: str) -> str:
    """Mask API token for safe logging."""
    if len(token) < 10:
        return "***"
    return f"{token[:3]}...{token[-3:]}"

# Usage
logger.info(f"Using bot token: {mask_token(settings.telegram_bot_token)}")
```

---

## Deployment Checklist

### Development
- [ ] `.env` file exists locally
- [ ] Secrets are not hardcoded
- [ ] Logs don't expose secrets

### Production
- [ ] Use environment variables (not `.env` file)
- [ ] Secrets managed via vault/secret manager
- [ ] Database credentials use least-privilege
- [ ] CORS properly configured
- [ ] HTTPS enabled

### Docker
```dockerfile
# NEVER bake secrets into Dockerfile
ENV TELEGRAM_BOT_TOKEN=xxx  # ❌ WRONG

# DO pass at runtime
docker run -e TELEGRAM_BOT_TOKEN=$TOKEN  # ✓ CORRECT
```

---

## Incident Response: Exposed Secret

If a secret is accidentally exposed:

1. **Immediately revoke/regenerate** the exposed credential
2. **Update `.env`** with new value
3. **Check git history** for exposure:
   ```bash
   git log -p --all -- .env
   ```
4. **If committed**, purge from history:
   ```bash
   # Using BFG Repo-Cleaner
   bfg --delete-files .env
   git reflog expire --expire=now --all
   git gc --prune=now --aggressive
   ```
5. **Force push** (team coordination required):
   ```bash
   git push --force
   ```

---

## AI-Specific Guidelines

### When Asking AI for Help

| Do | Don't |
|----|-------|
| Share code structure | Share actual credentials |
| Use placeholder values | Copy-paste from `.env` |
| Describe error messages | Share full stack traces with secrets |
| Ask about patterns | Ask "is this token valid?" |

### Example Safe Prompt
```
"I'm getting a 401 error from Telegram Bot API.
My token format is: 1234567890:ABCdef...
What are common causes?"
```

### Example Unsafe Prompt
```
"My bot token 1234567890:ABCdefGHIjklMNOpqrsTUVwxyz 
is not working. Help!"
```

---

## Quick Reference

| Secret | Where to Get | Rotation |
|--------|-------------|----------|
| `TELEGRAM_BOT_TOKEN` | @BotFather on Telegram | Create new bot |
| `TELEGRAM_CHAT_ID` | @userinfobot on Telegram | N/A (your ID) |
| `SECRET_KEY` | `openssl rand -hex 32` | Regenerate anytime |
| `CCXT_API_KEY` | Exchange API settings | Exchange dashboard |

---

## Verification Commands

```bash
# Check .env is ignored
git check-ignore .env

# Check for accidental commits
git log --all --full-history -- .env

# Verify no secrets in codebase
grep -r "TELEGRAM_BOT_TOKEN=" --include="*.py" src/

# Check file permissions
ls -la .env  # Should be -rw------- (600)
```

---

**Remember:** AI assistants are powerful tools, but treat all conversations as potentially visible to third parties. When in doubt, use placeholders.
