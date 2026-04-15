# Render.com ga joylash uchun qo'llanma

## 🚀 Render.com ga joylash

### 1️⃣ GitHub ga yuklash
```bash
git init
git add .
git commit -m "Initial commit"
git branch -M main
git remote add origin https://github.com/username/botlar.git
git push -u origin main
```

### 2️⃣ Render.com da yangi service yaratish
1. [render.com](https://render.com) ga kirish
2. "New +" → "Web Service"
3. GitHub repository ni tanlash
4. Quyidagi sozlamalar:
   - **Name**: `telegram-bot`
   - **Environment**: `Python 3`
   - **Branch**: `main`
   - **Root Directory**: `.` (bo'sh qoldiring)
   - **Runtime**: `Python 3`
   - **Build Command**: `pip install -r requirements.txt`
   - **Start Command**: `gunicorn app:app`

### 3️⃣ Environment Variables qo'shish
Render dashboard → Environment → Add Environment Variable:
```
TOKEN=8704916545:AAFXQMIiQDy7viSehEDAhF0XlX2_euTFbro
ADMIN_IDS=5475526744,5687217504
```

### 4️⃣ Deploy
- "Create Web Service" tugmasini bosing
- Avtomatik deploy boshlanadi (2-3 daqiqa)

### 5️⃣ Test qilish
Deploy tugagandan so'ng:
- Web service URL: `https://telegram-bot.onrender.com`
- Health check: `https://telegram-bot.onrender.com/health`

## 🔧 Muhim eslatmalar

### Database muammosi
Render ephemeral storage ishlatgani uchun database yo'qolishi mumkin:
- **Yechim**: PostgreSQL qo'shish yoki file-based backup

### Bot token xavfsizligi
- Tokenni hech qachon GitHub ga yuklamang!
- Faqat Render environment variables da saqlang

### Auto-restart
Render 15 daqiqada ishlamasa avtomatik restart qiladi

## 📊 Monitoring
```bash
# Loglarni ko'rish
curl https://telegram-bot.onrender.com/health

# Bot status
https://telegram-bot.onrender.com/
```

## 🔄 Update qilish
```bash
# Kod o'zgartirgandan so'ng
git add .
git commit -m "Update bot features"
git push origin main
# Render avtomatik deploy qiladi
```

## 💡 Qo'shimcha tips
- Free plan: 750 soat/oy
- Sleep: 15 daqiqa idle dan keyin
- Cold start: 30-60 soniya
- Backup: har kuni database ni yuklab oling
