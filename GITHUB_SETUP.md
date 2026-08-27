# Push ke GitHub - Step by Step

## Prerequisites

Anda perlu:
1. **GitHub account** (gratis di https://github.com)
2. **SSH key atau Personal Access Token** untuk authentication
3. **Git** (sudah installed di VPS)

---

## 🔑 Step 1: Setup GitHub SSH Authentication

### Option A: SSH Key (Recommended)

**Generate SSH key (if you don't have one):**
```bash
ssh-keygen -t ed25519 -C "faidzagustiawan@gmail.com"
# Press Enter untuk default path
# Press Enter untuk empty passphrase (atau set password)
```

**Copy public key:**
```bash
cat ~/.ssh/id_ed25519.pub
```

**Add to GitHub:**
1. Buka https://github.com/settings/keys
2. Click "New SSH key"
3. Paste public key content
4. Click "Add SSH key"

**Test:**
```bash
ssh -T git@github.com
# Should output: Hi USERNAME! You've successfully authenticated...
```

### Option B: Personal Access Token

1. Buka https://github.com/settings/tokens
2. Click "Generate new token" → "Generate new token (classic)"
3. Set scopes: `repo` (full control of private repositories)
4. Click "Generate token"
5. Copy token (save di tempat aman!)

---

## 📝 Step 2: Create GitHub Repository

1. Buka https://github.com/new
2. **Repository name:** `finance-tracker-dashboard`
3. **Description:** Personal finance tracker with web dashboard
4. **Visibility:** Public (agar orang bisa clone)
5. **Initialize:** Leave empty (sudah punya local repo)
6. Click "Create repository"

---

## 🚀 Step 3: Push to GitHub

**Di VPS Anda:**

```bash
cd /home/ubuntu/projects/finance-tracker-dashboard

# Add GitHub remote
git remote add origin git@github.com:YOUR_USERNAME/finance-tracker-dashboard.git

# Or jika pakai HTTPS + token:
# git remote add origin https://github.com/YOUR_USERNAME/finance-tracker-dashboard.git

# Rename branch ke 'main' (optional, tapi recommended)
git branch -M main

# Push to GitHub
git push -u origin main
```

**Expected output:**
```
Enumerating objects: 13, done.
Counting objects: 100% (13/13), done.
Delta compression using up to 4 threads
Compressing objects: 100% (11/11), done.
Writing objects: 100% (13/13), 6.58 KiB | 1.64 MiB/s, done.
Total 13 (delta 0), reused 0 (delta 0), reused pack 0 (delta 0)
To github.com:YOUR_USERNAME/finance-tracker-dashboard.git
 * [new branch]      main -> main
Branch 'main' set up to track remote branch 'main' from 'origin'.
```

✅ Done! Repo sekarang live di GitHub!

---

## ✅ Verify

Buka di browser:
```
https://github.com/YOUR_USERNAME/finance-tracker-dashboard
```

Anda akan lihat:
- ✅ All files (finance_tracker.py, api_server.py, dashboard/, etc)
- ✅ README.md displayed
- ✅ Commit history
- ✅ Install.sh executable

---

## 🔄 Workflow untuk Update Selanjutnya

Setiap kali ada changes:

```bash
# 1. Commit locally
git add .
git commit -m "Feature: Add export to CSV"

# 2. Push to GitHub
git push origin main

# 3. Verify di browser
# https://github.com/YOUR_USERNAME/finance-tracker-dashboard
```

---

## 📋 Troubleshooting

### Error: "Permission denied (publickey)"
```bash
# SSH key tidak setup
ssh-add ~/.ssh/id_ed25519
ssh -T git@github.com
```

### Error: "Repository not found"
```bash
# Username salah atau repo belum dibuat
# Pastikan:
# 1. Repo sudah dibuat di GitHub
# 2. Username benar di remote URL
git remote -v  # Check current remote
```

### Error: "fatal: Not a git repository"
```bash
# Pastikan di folder yang tepat
cd /home/ubuntu/projects/finance-tracker-dashboard
git status
```

### Want to change remote URL?
```bash
git remote set-url origin git@github.com:NEW_USERNAME/repo.git
git remote -v  # Verify
```

---

## 🎯 Next Steps

1. **Add License:** (Optional)
   ```bash
   # Create LICENSE file
   echo "MIT License" > LICENSE
   git add LICENSE
   git commit -m "Add MIT license"
   git push origin main
   ```

2. **Add GitHub Actions** (Optional, untuk CI/CD)
   - Create `.github/workflows/test.yml` untuk automated testing

3. **Share repo link:**
   ```
   https://github.com/YOUR_USERNAME/finance-tracker-dashboard
   ```

4. **Promote:**
   - Add to GitHub profile README
   - Share di dev communities
   - Create releases/tags untuk versioning

---

**Done! Aplikasi Anda sekarang di GitHub!** 🎉
