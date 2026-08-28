# Suv Sotuv Boti

Nukusdagi suv sotuvchi kompaniya uchun Telegram bot + Mini App.
Reja hujjatlaridagi barcha bo'limlarga (asosiy reja, 1- va 2-qo'shimchalar)
mos qurilgan: xavfsizlik, do'kon ro'yxatga olish, savat asosidagi buyurtma UX,
mahsulot CRUD, reklama, hisobotlar, qidiruv, minnatdorchilik xabarlari.

## Arxitektura

```
bot/                  — aiogram 3 backend (Python)
  config.py           — .env orqali sozlamalar
  database/           — SQLAlchemy modellari (SQLite)
  middlewares/         — xavfsizlik: ro'yxatdan o'tmaganlarni bloklaydi
  locales/            — o'zbek/rus matnlari
  handlers/
    common.py         — /start (do'kon, agent, va ro'yxatga olish havolasi)
    agent/            — faqat agent uchun: ro'yxatga olish, mahsulotlar,
                         reklama, qidiruv, hisobot
  services/           — buyurtma, hisobot, backup logikasi
  webapp_api/         — Mini App uchun JSON API (aiohttp)
  scheduler.py        — haftalik backup, oylik hisobot, navbatdagi reklama
  main.py             — hammasini birlashtiruvchi kirish nuqtasi

webapp/               — Telegram Mini App (React + Vite)
  src/pages/Catalog.jsx        — do'konchi: katalog, savat, tasdiqlash
  src/pages/AgentDashboard.jsx — agent: grafikli hisobotlar (Recharts)
  src/pages/AgentSearch.jsx    — agent: do'konchilarni qidirish
```

Bot va Mini App API bitta jarayonda ishlaydi (bitta aiohttp server) — 0.5 GB
xotira chegarasida ikkita alohida server yuritishdan qochish uchun.

### Muhim dizayn qarori: Mini App komponent kutubxonasi

Kengaytirilgan rejada `@telegram-apps/telegramui` tavsiya qilingan edi. Bu loyihada
o'rniga Telegram'ning **rasmiy CSS theme o'zgaruvchilari**
(`--tg-theme-bg-color` va h.k.) asosida qo'lda yozilgan, yengil interfeys
ishlatildi. Sabab: bu muhitda internetga chiqish imkoni yo'q, shuning uchun
uchinchi tomon kutubxonaning joriy versiyasini haqiqiy `npm install` bilan
sinab ko'rish imkonsiz edi. Natija baribir Telegram'ning o'z rangiga
(light/dark) avtomatik moslashadi va "begona ilova" emas, native ko'rinishda
— shunchaki tashqi bog'liqlik kamroq va ishonchliroq. Agar xohlasangiz,
`webapp/src` ichida `@telegram-apps/telegramui`'ga o'tish qiyin emas.

## Tekshirilgan narsalar

- Barcha Python fayllar `py_compile` orqali sintaksis jihatdan tekshirildi ✅
- Barcha JS/JSX fayllar `esbuild` orqali sintaksis jihatdan tekshirildi ✅
- **Tekshirilmagan**: haqiqiy `pip install` / `npm install` / ishga tushirish —
  bu muhitda internetga chiqish yo'q. GitHub'ga joylashtirgach, Railway
  build paytida haqiqiy o'rnatish va ishga tushirishni bajaradi. Kichik
  muammolar (masalan paket versiyasi to'qnashuvi) chiqib qolsa, Railway build
  loglarida aniq ko'rinadi — shunga qarab tuzatish kerak bo'lishi mumkin.

## Lokal ishga tushirish (bot, polling rejimida)

```bash
python -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
cp .env.example .env
# .env faylida BOT_TOKEN va AGENT_IDS'ni to'ldiring
python -m bot.main
```

Polling rejimida (WEBHOOK_BASE_URL bo'sh) Mini App API ishlamaydi — faqat
bot buyruqlari orqali test qilish mumkin. Mini App'ni to'liq sinash uchun
webhook rejimi va ochiq URL (masalan ngrok yoki Railway) kerak.

Mini App'ni alohida lokal ishga tushirish (frontend dizaynini ko'rish uchun,
API'siz):

```bash
cd webapp
npm install
npm run dev
```

## GitHub'ga yuklash

```bash
cd suv-sotuv-bot
git init
git add .
git commit -m "Suv sotuv boti — boshlang'ich versiya"
git branch -M main
git remote add origin https://github.com/<username>/suv-sotuv-bot.git
git push -u origin main
```

## Railway'ga deploy qilish

1. [railway.app](https://railway.app) da yangi loyiha yarating → **Deploy from
   GitHub repo** → shu repositoriyani tanlang.
2. Railway `Dockerfile`ni avtomatik aniqlaydi (qo'shimcha sozlash shart emas).
3. **Variables** bo'limida quyidagilarni kiriting (`.env.example`ga qarang):
   - `BOT_TOKEN`
   - `AGENT_IDS`
   - `AGENT_CONTACT_PHONE`
   - `WEBHOOK_SECRET` (o'zingiz o'ylab toping)
   - `DB_PATH` — agar Volume ulasangiz, masalan `/data/suv_bot.db`
4. Birinchi deploy tugagach, Railway domenini oling (Settings → Networking →
   Generate Domain), masalan `https://suv-bot-production.up.railway.app`.
5. Shu domenni `WEBHOOK_BASE_URL` va `WEBAPP_URL` qiymatlariga qo'shing va
   qayta deploy qiling (Railway avtomatik qayta ishga tushiradi).
6. **Muhim — ma'lumotlar saqlanishi**: Railway'ning standart fayl tizimi har
   bir deployda tozalanadi. SQLite bazangiz yo'qolib qolmasligi uchun
   **Volume** qo'shing (Settings → Volumes → Add Volume, masalan `/data`ga
   ulang) va `DB_PATH=/data/suv_bot.db` qilib belgilang.
7. BotFather'da Mini App tugmasini sozlash uchun `/mybots` → botingiz →
   **Bot Settings → Menu Button** → URL sifatida `WEBAPP_URL` qiymatini bering
   (bu ixtiyoriy — bot allaqachon inline "Katalogni ochish" tugmasi orqali
   Mini App'ni ochadi).

## Agent uchun birinchi qadamlar

1. O'z Telegram ID'ingizni bilib oling (masalan @userinfobot orqali) va uni
   Railway'dagi `AGENT_IDS` o'zgaruvchisiga qo'shing.
2. Botga `/start` yozing — agent menyusi chiqadi.
3. "➕ Yangi do'kon" orqali birinchi do'konni ro'yxatga oling. Oxirida sizga
   havola (deep-link) beriladi — shu havolani do'konchining o'ziga yuboring
   yoki uning telefonida oching. Havola bosilgach, do'kon avtomatik ulanadi.
4. "📦 Mahsulotlar" orqali kamida bitta mahsulot qo'shing — aks holda katalog
   bo'sh ko'rinadi.

## Bilib qo'yish kerak bo'lgan cheklovlar (keyingi bosqich uchun)

- Agent paneli hozircha faqat o'zbek tilida (9-bo'limdagi "agent qulay tilni
  tanlaydi" imkoniyati keyinroq qo'shilishi mumkin).
- Mahsulotni "butunlay o'chirish" ataylab yo'q — faqat yashirish. Bu 6-bo'lim
  va 10-bo'limdagi "eski buyurtmalar tarixi buzilmasligi" talabiga mos.
- `MemoryStorage` FSM uchun ishlatiladi — bitta Railway instance uchun
  yetarli. Agar kelajakda bir nechta instance kerak bo'lsa, Redis storage'ga
  o'tish kerak bo'ladi.
- Reklama "navbatga qo'yish" tekshiruvi har 30 daqiqada ishlaydi
  (`bot/scheduler.py`) — soat 10:00 dan keyin yuborilgan xabar aynan
  10:00'da emas, keyingi tekshiruvda (eng ko'pi 30 daqiqa kechikish bilan)
  yuboriladi. Talab qilinmagan aniqlik uchun kifoya.
