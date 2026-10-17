# 🎬 Film katalogi Telegram boti (UZ / RU)

Python va `python-telegram-bot` asosida yozilgan ikki tilli film katalogi. To‘lov tizimi yo‘q. Bot film posteri, tavsifi, yil, janr, reyting, davomiylik va tomosha manbasini ko‘rsatadi.

## Imkoniyatlar

- O‘zbekcha va ruscha interfeys; tanlangan til ma’lumotlar bazasida saqlanadi.
- Film katalogi va sahifalash.
- Film nomi, tavsifi va janri bo‘yicha qidiruv.
- Janrlar bo‘yicha filtrlash.
- Sevimlilar ro‘yxati va ko‘rilgan filmlar tarixi.
- Poster va film metama’lumotlari.
- Tomosha qilish uchun HTTPS manzil yoki Telegram video `file_id`.
- Administrator orqali film qo‘shish, o‘chirish va statistika.
- Lokal SQLite yoki PostgreSQL bazasi.
- Render Web Service uchun webhook rejimi; kompyuterda polling rejimi.

> **Kontent eslatmasi:** botga faqat o‘zingizga tegishli, ommaviy domenidagi yoki tarqatish/tomosha qilish uchun ruxsat olingan videolarni yuklang. Bot noqonuniy nusxalarni qidirish yoki himoyani aylanib o‘tish funksiyasini bajarmaydi.

## 1. BotFather orqali bot tokenini olish

1. Telegram’da [@BotFather](https://t.me/BotFather) ni oching.
2. `/newbot` buyrug‘ini yuboring.
3. Bot nomi va username’ni kiriting.
4. Berilgan tokenni maxfiy saqlang. Uni hech kimga yubormang va GitHub’ga joylamang.

## 2. Loyihani kompyuterda ishga tushirish (Windows)

1. ZIP arxivni oching.
2. Kompyuterda Python 3.11 yoki yangiroq versiyasini o‘rnating: https://www.python.org/downloads/ . O‘rnatishda **Add Python to PATH** belgisini belgilang.
3. Loyiha papkasida terminal/CMD oching.
4. Virtual muhit yarating va faollashtiring:

   ```bat
   py -m venv .venv
   .venv\Scripts\activate
   ```

5. Kutubxonalarni o‘rnating:

   ```bat
   pip install -r requirements.txt
   ```

6. `.env.example` faylidan nusxa oling va nusxa nomini `.env` qiling. `.env` ichidagi `BOT_TOKEN` qiymatini BotFather bergan token bilan almashtiring. `ADMIN_IDS` qatoriga o‘z Telegram ID raqamingizni kiriting.
7. Telegram’da botni ochib `/myid` yuboring. Chiqqan raqam — sizning Telegram ID’ingiz.
8. Botni ishga tushiring:

   ```bat
   python bot.py
   ```

`moviebot.db` fayli avtomatik yaratiladi. Lokal rejimda webhook emas, polling ishlatiladi. To‘xtatish uchun terminalda `Ctrl+C` bosing.

## 3. Render’ga joylash

### A. Kodni GitHub’ga yuklash

1. https://github.com/ saytida yangi repository yarating, masalan `film-telegram-bot`.
2. ZIP ichidagi **fayllarni** repository’ga yuklang: `bot.py`, `database.py`, `requirements.txt`, `render.yaml` va boshqalar. ZIP faylining o‘zini emas, ochilgan ichidagi fayllarni yuklang.
3. `.env` faylini GitHub’ga yuklamang. U maxfiy tokenni saqlaydi.

### B. Render’da xizmat yaratish

1. https://render.com/ saytiga kiring va GitHub’ni ulang.
2. Dashboard’da **New + → Blueprint** ni tanlang (yoki New + → Web Service va GitHub’dagi repository’ni tanlang).
3. `render.yaml` topilsa, undagi `film-catalog-telegram-bot` xizmatini tasdiqlang.
4. Render’da xizmatning **Environment** bo‘limini ochib quyidagilarni kiriting:
   - `BOT_TOKEN` — BotFather bergan token.
   - `ADMIN_IDS` — sizning raqamli Telegram ID’ingiz. Bir nechta admin bo‘lsa: `123456,789012`.
   - `DATABASE_URL` — xohlasangiz PostgreSQL ulanish manzili. Lokal testdan boshqa holatda bu tavsiya etiladi.
5. **Deploy** tugmasini bosing va **Logs** bo‘limida build hamda ishga tushish xabarlarini tekshiring.

`render.yaml` quyidagi buyruqlarni ishlatadi:

- Build: `pip install -r requirements.txt`
- Start: `python bot.py`

Render `RENDER_EXTERNAL_URL` va `PORT` qiymatlarini o‘zi beradi. Bot shu URL’da Telegram webhook’ni avtomatik sozlaydi. Web Service uchun health-check path talab qilinmaydi.

## 4. Ma’lumotlar bazasini saqlash

- **Lokal kompyuterda:** SQLite (`moviebot.db`) yetarli.
- **Render bepul Web Service’da:** lokal fayl tizimi vaqtinchalik. Qayta ishga tushish, uyqudan uyg‘onish yoki redeploy paytida SQLite fayli yo‘qolishi mumkin. Faqat sinov uchun foydalaning yoki PostgreSQL sozlang.
- **Render PostgreSQL:** Render’da database yarating va xizmatga `DATABASE_URL` environment variable sifatida uning connection string’ini ulang. Agar database URL `postgres://` yoki `postgresql://` bo‘lsa, kod uni `psycopg` formatiga moslashtiradi.
- Render’ning bepul PostgreSQL rejasi muddati cheklangan bo‘lishi mumkin (joriy limitlarni Render hujjatlaridan tekshiring). Muhim ma’lumotlar uchun doimiy saqlash rejasi va zaxira nusxalarini ko‘zda tuting.

Rasm va video fayllar Telegram serverida saqlanadi; baza ichida Telegram `file_id` saqlanadi. Baza yo‘qolsa, poster/video ID’lari ham katalog yozuvlari bilan birga yo‘qoladi.

## 5. Admin buyruqlari

Avval `ADMIN_IDS` to‘g‘ri kiritilgan bo‘lishi kerak.

- `/myid` — o‘z Telegram ID’ingizni ko‘rish.
- `/addfilm` — film qo‘shish bo‘yicha ketma-ket savollarni boshlash.
- `/deletefilm 12` — ID raqami 12 bo‘lgan filmni o‘chirish.
- `/stats` — film va foydalanuvchilar statistikasini ko‘rish.
- `/cancel` — film qo‘shishni bekor qilish.
- `/cancel_search` — qidiruvni bekor qilish.

Film qo‘shish jarayonida ikki tildagi nom, yil, har ikki tildagi janr va tavsif, reyting, davomiylik, poster va tomosha manbasi kiritiladi. Poster uchun rasmni Telegram’da **photo** sifatida yuboring. Tomosha manbasi sifatida HTTPS havolani berish yoki `VIDEO` deb yozib, ruxsatli videoni botga jo‘natish mumkin. Video botga qayta yuklanmaydi: Telegram `file_id` orqali yuboriladi.

## 6. Tekshirish

1. Telegram’da botingizga `/start` yuboring.
2. 🌐 Til tugmasidan o‘zbek yoki rus tilini tanlang.
3. Admin sifatida `/addfilm` bilan test yozuv yarating.
4. Katalog, qidiruv, janrlar, sevimlilar va ko‘rilganlar tugmalarini tekshiring.
5. Render Logs’da `Database initialized; bot is ready.` xabari chiqishini tekshiring.

## Xavfsizlik

- Bot tokenini hech qachon ochiq joylamang.
- `ADMIN_IDS` ga faqat ishonchli adminlarning raqamli Telegram ID’larini kiriting.
- HTTPS manzillarini ishlating.
- Film va video uchun tegishli tarqatish huquqiga ega ekaningizni tekshiring.
- Render’da GitHub repository’ga `.env` faylini yubormang.

## Fayllar

- `bot.py` — Telegram interfeysi, tillar, katalog, qidiruv va admin dialogi.
- `database.py` — SQLite/PostgreSQL bazasi va saqlash funksiyalari.
- `requirements.txt` — Python kutubxonalari.
- `render.yaml` — Render konfiguratsiyasi.
- `.env.example` — environment sozlamalari namunasi.
