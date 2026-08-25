# Bot API 10.3 va undan keyin qo'shilgan imkoniyatlar

Bu fayl `5816469` commitidan keyin qo'shilgan hamma narsani tushuntiradi:
qaysi imkoniyat qayerda, qanday ishlaydi va **nega aynan shunday** yozilgan.

`CLAUDE.md` — qisqa qoidalar to'plami (nimaga tegmaslik kerak).
Bu fayl — to'liq tushuntirish (nima qanday ishlaydi).

Tegishli commitlar:

| Commit | Mavzu |
|---|---|
| `391565b` | Bot API 10.3 to'plami, chatga internet rasmlari, `deck` maketlari |
| `0578dea` | Taqdimot sifat tekshiruvi, matnning avtomatik sig'ishi |
| `ad61056` | Oraliq xabar (keyingi commitda qaytarilgan) |
| `c22a413` | Oraliq xabar va status nosozliklari |
| `5560bdd` | Oraliq xabar olib tashlandi |
| `ed58cc0` | Ko'p qatorli nusxa tugmasi tuzatildi |
| `db76465` | Nusxa tugmasi yozuvsiz, faqat ikonka |

---

## 1. Boy xabarlar (rich message)

Bot API 10.3 `sendRichMessage` metodini qo'shdi. Oddiy `sendMessage` dan
farqi: xabar ichida jadval, yig'iladigan sitata, media bloklari va
tugmalar bo'lishi mumkin.

**Qayerda:** `handlers/messages.py:380` — `_send_rich_message()`.

### Format tanlash — eng ko'p xato qilinadigan joy

`_rich_message_payload()` ([messages.py:321](handlers/messages.py#L321))
`html` yoki `markdown` maydonidan **bittasini** to'ldiradi. Bular ikkita
mustaqil rejim:

- `html` — `<tg-thinking>`, `<tg-emoji>` kabi teglar faqat shu yerda ishlaydi;
- `markdown` — oddiy markdown + cheklangan HTML.

⚠️ HTML-only tegni `markdown` maydoniga qo'ysangiz, parser butun xabarni
parslashni to'xtatadi va hatto oddiy `*qalin*` ham xom holda ko'rinadi.

### Markdown tayyorlash

`services/ai.py:370` — `build_rich_markdown()`. Tartib **muhim**:

1. `_protect_spans()` — kod bloklari va inline kodni chiqarib qo'yadi;
2. `_compact_tables()` — GFM jadvalini `<table compact>` ga o'giradi;
3. matematika (`$...$` → `<tg-math>`), sanalar (`<tg-time>`);
4. `_restore_spans()` — kod joyiga qaytadi;
5. `_collapse_sources()` — manbalar ro'yxatini `<blockquote expandable>` ga o'raydi.

Jadval **birinchi** o'giriladi: (a) kod ichidagi `|` jadvalga o'xshaydi,
(b) katak matni html-escape qilinadi, ya'ni undan oldin qo'yilgan
`<tg-time>` teglari oddiy matnga aylanib qolardi.

`_EXPANDABLE_ATTR = "expandable"` — bir so'zli kalit, chunki API
hujjatining o'zi ziddiyatli (tur jadvalida `collapsed` deb yozilgan).

### Chegaralar

| Nima | Chegara |
|---|---|
| Xabar uzunligi | 32768 belgi |
| Bloklar soni | 500 |
| Media | 50 |
| Jadval ustunlari | 20 |
| Media havolasi | faqat HTTP/HTTPS (Telegram o'zi tortadi) |

---

## 2. Status animatsiyasi va to'xtatish tugmasi

`sendRichMessageDraft` — chatda "yozmoqda" ko'rinishidagi vaqtinchalik
xabar. `can_stop=True` bo'lsa unda to'xtatish tugmasi paydo bo'ladi.

**Qayerda:** `handlers/messages.py:338` — `_send_rich_draft()`,
`process_stream_draft()` ichidagi `emoji_animator()`.

### aiogram bilmaydigan ikkita narsa

**1. Yangi update turi.** Tugma bosilganda Telegram
`stopped_message_generation` update yuboradi. aiogram 3.29 bu turni
bilmaydi — `Update.event_type` unda **istisno otadi**. Shuning uchun u
`main.py` dagi `dp.update.outer_middleware` da ushlanadi: middleware
`event_type` aniqlanishidan OLDIN ishlaydi, xom maydon esa aiogram
modellari `extra="allow"` bo'lgani uchun saqlanib qoladi.

**2. `allowed_updates`.** aiogram bu ro'yxatni ro'yxatdan o'tgan
ishlovchilardan chiqaradi. Bu tur uchun ishlovchi yo'q, ya'ni Telegram
update'ni **umuman yubormasdi** — tugma jimgina ishlamasdi. Shuning
uchun `start_polling` ga ro'yxat ANIQ beriladi:

```python
allowed = dp.resolve_used_update_types()
if "stopped_message_generation" not in allowed:
    allowed.append("stopped_message_generation")
await dp.start_polling(bot, allowed_updates=allowed)
```

### To'xtatish oqimni ham uzadi

`_next_or_stop()` ([messages.py](handlers/messages.py)) generatordan
keyingi bo'lakni va to'xtatish signalini `asyncio.wait(...,
FIRST_COMPLETED)` bilan **birga** kutadi. Busiz qidiruv yoki fayl
vazifasi ichida turgan oqim tugma bosilganda ham 1-2 daqiqa davom
etardi va o'sha tokenlar baribir hisoblanardi.

To'xtatilganda `stream_generator.aclose()` chaqiriladi.

### Draft faqat shaxsiy chatda

Telegram cheklovi. Shuning uchun ikkita alohida bayroq bor:

- `using_rich_draft` — animatsiya va to'xtatish tugmasi (faqat DM);
- `can_send_rich` — bezakli yakuniy xabar (guruhda ham ishlaydi).

Ilgari ikkalasi bitta bayroqda edi va **guruhdagi javob bezaksiz
ketardi** — jadval, yig'iladigan manbalar va rasmlar guruhda umuman
ko'rinmasdi.

### Status matnlari

`STATUS_TEXTS_BY_TYPE` ([messages.py:558](handlers/messages.py#L558)) —
har bir asbob uchun alohida ro'yxat: `text`, `photo`, `document`,
`voice`, `search`, `file_task`, `image`, `reminder`, `memory`.

`services/ai.py` tool chaqirilganda `[STATUS]<tur>` bo'lagini yuboradi,
`process_stream_draft` esa `active_type` ni almashtiradi. Matn ham,
premium emoji ham shunga qarab o'zgaradi.

⚠️ `update_memory` uchun alohida shox **shart**: usiz chaqiruv pastdagi
`elif not search_performed` ga tushib, model shunchaki ismni
saqlayotganda ekranda "Internetdan ma'lumot qidirilmoqda" degan
**yolg'on status** turardi. `tests/test_tool_status.py` buni qo'riqlaydi.

---

## 3. Tugmalar

### Uch xil tugma, uch xil imkoniyat

| Tur | Qayerda | Premium ikonka | Nusxa (`copy_text`) |
|---|---|---|---|
| `InlineKeyboardButton` | xabar ostida | ✅ `icon_custom_emoji_id` | ✅ |
| `<tg-button>` | xabar **ichida** | ❌ | ✅ |
| `<tg-button-row>` | xabar ichida, 1-8 ta | ❌ | — |

### Uslublar — yetkazib berish masalasi

Telegram faqat `primary` / `success` / `danger` ni qabul qiladi. Boshqa
qiymat **butun xabarni** rad ettiradi. Shuning uchun `pro_module.btn()`
va `BTN_*` konstantalari ishlatiladi.

`BTN_LINK` ("link") — istisno: u faqat rich xabar ichidagi
`<tg-button>` uchun va faqat callback tugmalarda. `btn()` uni ataylab
qabul qilmaydi.

### O'chirilgan tugma (`disabled`)

Bot API 10.3. Tugma ko'rinadi, lekin bosilmaydi. Kunlik daydjest
ekranida bepul foydalanuvchiga soat panjarasi shunday ko'rsatiladi —
"Pro imkoniyati" degan quruq matn nima yo'qotilayotganini
ko'rsatmaydi, ko'rinib turgan panjara esa ko'rsatadi.

⚠️ `disabled` — tugmaning **tur maydoni**. Telegram "turni belgilaydigan
maydonlardan aniq bittasi bo'lsin" deb talab qiladi, shuning uchun u
bilan birga `callback_data`/`url` yuborilmaydi. `_downgrade_kb()` ham
uni ko'chirishi shart, aks holda zaxira klaviaturada tursiz tugma
qolib, butun xabar rad etiladi.

### Xabar ichidagi tugma va qator ajratuvchi (jonli nosozlik)

`rich_button()` HTML yasaydi, ya'ni matn qochirilishi shart. Lekin
**qo'shtirnoqni qochirish yetarli emas**:

`html.escape()` qator ajratuvchini tegmasdan qoldiradi, Telegram parseri
esa atribut ichidagi xom `\n` ni ko'rib tegni o'sha yerda uzadi va
qolganini xom matn qilib chiqaradi. Foydalanuvchi tugma o'rniga
`<tg-button type="copy_text" text="...">` yozuvini ko'rardi.

`_attr_value()` ([pro.py:111](handlers/pro.py#L111)) `\n` ni `&#10;` ga
o'giradi — parser uchun oddiy belgi, nusxa olinganda esa klient uni
haqiqiy qator ajratuvchiga qaytaradi. **Aynan shu ko'p qatorli kodni
nusxalashni ishlatadi.**

### "Nusxa olish" tugmasi

`_copy_button_html()` ([messages.py:699](handlers/messages.py#L699)).
Uch shart bir vaqtda bajarilsagina qo'yiladi:

1. javobda **aynan bitta** kod bloki (ikkitasi bo'lsa qaysi biri
   nusxalanishi noaniq — noaniq tugma tugmasizdan yomon);
2. blok **256 belgidan** oshmaydi — bu Bot API ning `CopyTextButton.text`
   uchun **qattiq chegarasi**, ko'tarib bo'lmaydi;
3. javob bitta xabarga sig'adi.

Yorliq — faqat `📋`, yozuvsiz. Butunlay bo'sh yorliq **mumkin emas**:
Telegram matnsiz tugmani rad etadi.

---

## 4. Guruhda ko'rinmas xabarlar (ephemeral)

`ephemeral_params()` ([messages.py:365](handlers/messages.py#L365)) —
xabarni faqat so'rov egasiga ko'rsatish. Shaxsiy chatda bo'sh `dict`
qaytadi, ya'ni chaqiruvchi kod o'zgarmaydi.

Nega kerak: "limit tugadi", "Pro reklamasi", "iltimos kuting" kabi
xabarlar **shaxsiy**, lekin guruhda hammaga ko'rinadi — bu botni
guruhdan chiqarib yuborishning eng keng tarqalgan sababi.

---

## 5. Chatga internet rasmlari

Foydalanuvchi "BMW M5 CS haqida rasm bilan ayt" deganda bot rasmni
**chizmaydi** — internetdan topib, chatga qo'yadi. Token sarflanmaydi.

**Oqim:**

```
internet_search(want_images=true)
   → _ddg_images_sync()        DuckDuckGo, safesearch="on"
   → _image_url_ok()           har bir URL tirikligini tekshiradi
   → images_out[]              chaqiruvchiga qaytadi
   → format_image_catalog()    modelga URL'SIZ ro'yxat beradi
   → model [rasm:1] deb yozadi
   → embed_images()            yuborishdan oldin media blokiga almashtiradi
```

### URL modelga ATAYLAB ko'rsatilmaydi

Ikki sabab: (a) har bir URL 30-60 token, (b) model ularni qayta yozib,
o'lik havolaga aylantiradi. Model faqat `[rasm:1]` / `[rasmlar]`
belgilarini ko'radi — jami ~25 token.

`embed_images()` ularni yuborish oldidan haqiqiy media blokiga
almashtiradi, `strip_image_tokens()` esa barcha zaxira yo'llardan va
oqim paytidagi draftdan tozalab tashlaydi (aks holda foydalanuvchi xom
`[rasm:1]` yozuvini ko'rardi).

**Telegram rasmni o'zi tortadi** — bot hech narsa yuklab olmaydi.

### Tiriklikni tekshirish

`_image_url_ok()` `HEAD` emas, `Range: bytes=0-0` bilan `GET` yuboradi —
ko'p CDN `HEAD` ga `405` qaytaradi va tirik rasm o'lik deb tashlanardi.
Haqiqiy hajm `Content-Range` sarlavhasidan o'qiladi.

### Xavfsiz qidiruv

`SEARCH_IMAGE_SAFESEARCH = "on"`. Kutubxonaning `moderate` standarti
yosh chegarasi yo'q bot uchun yetarli emas edi.

### Sozlamalar

`core/config.py:693` — `SEARCH_IMAGE_MAX = 4`, `CANDIDATES = 10`,
`HEAD_TIMEOUT = 4`, `SLIDESHOW_MIN = 2`.

---

## 6. Hujjat ichidagi rasmlar

Bu **butunlay boshqa mexanizm**. Chatdagi rasm bilan faqat qidiruv
chaqiruvi umumiy — ikkalasini chalkashtirish foydalanuvchi haqiqatda
duch keladigan nosozlik.

| | Chatda | Hujjatda |
|---|---|---|
| Nima uzatiladi | URL | baytlar |
| Kim yuklaydi | Telegram | bot |
| Belgisi | `[rasm:N]` | `rasm1.jpg` |

**Sabab:** sandbox tavsifi modelga "internet YO'Q" deb va'da beradi, va
aynan shu va'da kodni bashorat qilinadigan qiladi. Rasm olishni
so'ralgan model URL **o'ylab topadi**, o'ylab topilgan URL esa o'lik.

Shuning uchun teskari tartib: model `image_queries` da nima kerakligini
sanaydi → `_run_file_task` kod ishga tushishidan **oldin** yuklab oladi
→ `run_in_sandbox(extra_files=...)` ularni ish papkasiga `rasm1.jpg`,
`rasm2.jpg` deb qo'yadi.

**Pozitsion:** har so'rovga bitta fayl, topilmagani ham o'z raqamini
band qiladi — aks holda qolganlari siljib, model yozgan izoh boshqa
rasmga tushardi.

**Kesh:** fayl sikli 4 martagacha qayta ishlaydi. Keshsiz ikkinchi
yuklash modelga **boshqa** rasmlarni berardi — u esa izohni allaqachon
yozib bo'lgan.

**JPEG ga o'girish majburiy:** DuckDuckGo natijalarining katta qismi
WEBP, python-pptx esa WEBP ni qabul qilmaydi. Hammasi Pillow orqali
qayta kodlanadi (`FILE_IMAGE_MAX_SIDE = 1600`, sifat 85).

### Ikkala yo'lni ajratib turadigan narsa

Yo'naltirish **prompt darajasida va mo'rt**. Fayl tool tavsifiga "rasm"
so'zini qo'shish HAR QANDAY so'rovni ("olma haqida ma'lumot ber") fayl
vazifasiga aylantirib yuborgan edi.

Hozir ikkala tavsifda ham bir-biriga ishora qiluvchi ⛔️ bor, va
`IMAGE_CAPABILITY_NOTE` ([config.py:322](core/config.py#L322)) tizim
promptida turibdi — usiz model hech qanday tool chaqirmasdan "men rasm
yubora olmayman" deb javob yozardi.

⚠️ Bu izoh **faqat** `get_openai_reply` ga qo'shiladi. `get_vision_reply`
da qidiruv tooli yo'q, ya'ni u yerda bunday va'da yolg'on bo'lardi.

---

## 7. `deck.py` — taqdimot maketlari

`services/sandbox_helpers/deck.py` (~700 qator). Sandbox ichiga
avtomatik ko'chiriladi, model `import deck` qiladi.

### Nega kerak

Model shakllarni qo'lda `Inches(...)` bilan joylashtirganda ularning
haqiqiy o'lchamini **hech qachon hisoblamaydi**. Uchta xato doim bir xil
edi: rasm matn ustida, manba yozuvi rasm ustida, sahifa raqami rasm
ustida.

`docgen` PDF uchun matn metrikasini o'z ustiga olgani kabi, `deck` PPTX
uchun **butun geometriyani** o'z ustiga oladi. Modelga faqat mazmun
qoladi.

### Maketlar

`cover`, `section`, `bullets`, `image_slide`, `stats`, `table`, `quote`,
`closing`. Temalar: `navy`, `forest`, `plum`, `slate`.

### Rasm hovuzi va `AUTO`

```python
d = deck.Deck("Mavzu", theme="navy", images=["rasm1.jpg", "rasm2.jpg"])
d.bullets("Sarlavha", [...])          # rasm — avtomatik
d.table("Jadval", rows, image=None)   # rasm ATAYLAB kerak emas
```

Har bir maketning `image` parametri sukut bo'yicha `AUTO` sentineli.
Sabab: model "birinchi slaydda rasm bo'lsin" degan gapni **so'zma-so'z**
tushunadi va qolgan slaydlarni bo'sh qoldiradi. `AUTO` rasmni butun
taqdimot bo'ylab taqsimlaydi.

⚠️ `AUTO` ni `None` qilib bo'lmaydi: `image=None` — "bu slaydda rasm
kerak emas" degan **aniq** rad javobi.

### Ikki xil rasm joylash

- **`mode="fill"`** — yon ustundagi rasm. Matn kartochkasi bilan bir xil
  o'lcham va bir xil yuqori chekka, rasm esa ramkani to'liq to'ldirish
  uchun qirqiladi. Shu tufayli rasm masshtabi slayddan slaydga
  "sakramaydi".
- **`mode="fit"`** — asosiy fotosurat va diagramma. Qirqish xarita yoki
  grafikni yo'q qiladi, shuning uchun rasm butun ko'rinadi va
  **ramka rasmga yopishadi** (0.14" chekka bilan kichrayadi). Berilgan
  quti faqat chegara, chizilgan ramka emas. Izoh va manba qaytarilgan
  haqiqiy to'rtburchakdan hisoblanadi.

### Matnning avtomatik sig'ishi

PPTX ichida haqiqiy shrift metrikasi yo'q (PDF tomonda `docgen` uni
reportlab'dan oladi). Shuning uchun taxminiy hisob: o'rtacha belgi
kengligi ≈ 0.5 × shrift o'lchami, qator oralig'i 1.22.

`_shrink()` sarlavha yoki bandlar qutiga sig'maguncha shriftni
kichraytiradi (10% zaxira bilan). Busiz uzun sarlavha ikkinchi qatorga
tushib, ostidagi kontent ustiga chiqardi.

### Boshqa detallar

- Slaydlar orasida `fade` o'tish (xom XML orqali);
- Muqovada rasm — to'liq ekranli fon + qorayituvchi qatlam (`scrim=70`),
  usiz oq matn o'qilmaydi;
- Altbet uchun band joy (`FOOTER_H`), hech bir maket u yerga kontent
  qo'ymaydi;
- Shrift `Calibri` — `Verdana` da o'zbekcha `ʻ` yo'q.

---

## 8. Taqdimot sifat tekshiruvi

`d.save()` faylni saqlagach `check()` ni chaqiradi va hisobotni
stdout'ga chiqaradi. **AI chaqiruvi talab qilmaydi** — sof geometriya va
matn hisobi, ya'ni tekin va bir xilda takrorlanadi.

Tekshiriladi:

| Nima | Chegara |
|---|---|
| Slayd soni | 6-20 |
| Element slayddan chiqishi | 0.02" zaxira |
| Ustma-ustlik | kartochkalar (AUTO_SHAPE) hisobga olinmaydi |
| Slayddagi so'z soni | 40 (altbet va manba sanalmaydi) |
| Takroriy sarlavha | — |
| Namunaviy matn | `lorem ipsum`, `todo`, `tbd`, ... |

Hisobot:

```
[TEKSHIRUV] 11 slayd, 9 rasm, 2 muammo
  - 10-slayd: namunaviy matn qolib ketgan ('todo')
  - 10-slayd: sarlavha 9-slayd bilan bir xil ('xavflar')
DECK-CHECK-MUAMMO
```

Oxirgi qatorni `_run_file_task` ([ai.py:1705](services/ai.py#L1705))
ushlaydi va modeldan **tuzatishni** so'raydi. Mavjud 4 raundli sikl
buni bajaradi.

⚠️ **Oxirgi raundda so'ralmaydi** (`rounds_left > 1`) — aks holda
foydalanuvchi kamchiliksiz emas, umuman **faylsiz** qolardi.

⚠️ Fayl ro'yxatda qoladi. Model uni o'sha nom bilan qayta saqlaganda
`_merge_output()` eskisining **o'rnini oladi** — oddiy `extend` bo'lsa
foydalanuvchi bitta hujjatning ikki nusxasini olardi.

### Ish tartibi

`_DOC_DESIGN_GUIDE` ning `0)` bandi modelga ketma-ketlikni beradi:
tahlil → **fakt kerak bo'lsa `internet_search`** → hikoya chizig'i →
rasm so'rovlari → diagramma → yig'ish → tekshiruv → tuzatish.

Ilgari taqdimot faqat modelning xotirasidan yozilardi; o'qituvchi
tekshiradigan narsa esa aynan sana va raqamlar.

---

## 9. Ishonchlilik tuzatishlari

### Rad etilgan ≠ javob kelmagan

`_telegram_api_request` `outcome` chiqish parametri orqali **sababni**
xabar qiladi:

- `OUTCOME_REJECTED` — Telegram `ok:false` javob berdi;
- `OUTCOME_UNKNOWN` — timeout yoki aloqa uzildi.

Zaxira pog'onasi soddaroq shaklda **faqat REJECTED** da qayta uriniladi.
UNKNOWN da jimgina to'xtaydi, chunki xabar yetib borgan bo'lishi mumkin.

**Sabab:** umumiy aiohttp sessiyasi har bir chaqiruvni 10 soniyada
kesadi — bu 0.6s draft pinglari uchun to'g'ri, rasmli rich xabar uchun
esa noto'g'ri: Telegram xabarni yaratishdan oldin har bir rasmni manba
saytdan **o'zi yuklab oladi**. Klient timeout bo'lardi, pog'ona "rad
etildi" deb xulosa qilib qayta yuborardi, Telegram esa ikkalasini ham
yetkazardi — foydalanuvchi bir xil javobni ikki marta ko'rardi
(biri rasmli, biri rasmsiz).

Endi media bo'lgan xabarga `RICH_MEDIA_TIMEOUT = 60.0` beriladi.

### Serverda kutubxonalar import bo'lmay qolgani

Eng chalg'ituvchi nosozlik: mahalliy kompyuterda hammasi ishlardi,
Railway'da esa `import pptx` yiqilardi. Model `import deck` yiqilgach
jimgina PDF ga o'tib ketardi — foydalanuvchi **taqdimot so'rab PDF
olardi** va buni hech narsa bildirmasdi.

Ikkita mustaqil sabab, ikkalasi ham faqat Linuxda ko'rinadi
(`_HAS_RESOURCE` Windowsda `False`, ya'ni RLIMIT umuman qo'llanmaydi):

**1. `RLIMIT_AS` virtual manzil maydonini cheklaydi.** numpy, pandas,
matplotlib va pptx ularni ishlatmasa ham gigabaytlab manzil band qiladi
(arena, oqim steklari, mmap zaxirasi). 2 GB chegara `import pandas` ni
ham `MemoryError` bilan yiqitardi. Har safar boshqa kutubxona
yiqilgani uchun nosozlik "goh bor, goh yo'q" bo'lib ko'rinardi.

Yechim: `RLIMIT_DATA` (1.5 GB) — u **haqiqiy uyumni** cheklaydi
(Linux 4.7+ da anonim mmap ham kiradi). Himoya saqlanadi, bekorga band
qilingan manzil maydoni hisoblanmaydi.

**2. OpenBLAS oqimlari.** Birinchi sabab tuzatilgach `OpenBLAS error:
Memory allocation still failed after 10 retries` chiqa boshladi.
Konteyner ichida `nproc` **host** yadrolarini ko'rsatadi (Railway'da
o'nlab), OpenBLAS esa har bir oqim uchun katta bufer ajratadi.

Yechim: `OPENBLAS_NUM_THREADS=1` va sheriklari
(`OMP_/MKL_/NUMEXPR_NUM_THREADS`). Bular `PYTHON*` emas, shuning uchun
`-E` ularni bosmaydi. Sandbox kodi bir martalik hisob — parallellikdan
foyda yo'q.

**Nazorat:** `sandbox.check_libraries()` bot ishga tushganda 13 ta
kutubxonani **bola jarayonda** (sandbox bilan bir xil sharoitda) sinab
ko'radi va nosozlikni logga chiqaradi. Ota jarayonda `import pptx`
qilib tekshirish yetarli emas — u boshqa muhitni ko'radi.

Shu bilan birga fayl vazifasi xatosida endi traceback'ning **oxirgi**
satri logga tushadi: xatoning turi va xabari o'sha yerda. Ilgari
boshidan 200 belgi olinardi va logda `from pptx import Pre` degan
foydasiz bo'lak qolib, asl sabab ko'rinmasdi.

### Sandbox Windowsda UTF-8 emas edi

`-E` bayrog'i **barcha `PYTHON*` o'zgaruvchilarini** o'chiradi — shu
jumladan o'sha faylda qo'yilgan `PYTHONIOENCODING=utf-8` ni ham.
Linuxda `LANG=C.UTF-8` qutqaradi, Windowsda esa bola jarayon ANSI kod
sahifasiga tushadi va o'zbekcha `ʻ` chop etilishi bilan yiqiladi.

Model buni **o'z kodining xatosi** deb o'ylab, fayl raundlarini behuda
sarflaydi. Yechim: `-X utf8` — bu bayroq, env emas, shuning uchun `-E`
uni bosa olmaydi.

### Eslab qolingan fayl yangi topshiriqqa yopishishi

Bot yuborgan faylni 10 daqiqa eslab qoladi ("endi PDF qil" kabi davomiy
so'rovlar uchun). Foydalanuvchi katta yangi topshiriqni qayta
yuborganda, unga o'sha eski fayl biriktirilib, modelga "bu SEN yaratgan
fayl, davom ettir, noldan boshlamang" deyilardi.

Natijada model yangi taqdimot yasamay, eskisini **tekshirish** bilan
barcha raundlarni sarflab, faylsiz javob qaytarardi.

`_pending_for_request()` ([messages.py:1461](handlers/messages.py#L1461))
— eski fayl faqat **400 belgidan qisqa** so'rovga biriktiriladi. Davomi
doim qisqa bo'ladi; uzun xabar — yangi topshiriq.

### Ichki ma'lumot javobga chiqmaydi

Fayl vazifasi muvaffaqiyatsiz tugaganda modelga "muammoni tushuntiring"
deyilardi, lekin **nimani ko'rsatmaslik kerakligi** aytilmasdi. Model
traceback, `script.py`/`deck.py`, vaqtinchalik papka yo'llarini javobga
ko'chirardi.

`_NO_INTERNALS` ([ai.py:1593](services/ai.py#L1593)) barcha
muvaffaqiyatsiz yo'llarga qo'shiladi.

### Har raunddan keyin ekran tozalanadi

`[CLEAR_TEXT]` ilgari faqat `_SYNTHESIS_SYSTEM` birinchi marta
qo'shilganda ishlardi, ya'ni **ikkinchi** qidiruv raundidan keyin matn
qolib ketib, keyingi bosqichda yozilganiga yopishardi — foydalanuvchi
bitta xabarda ikkita "…tayyorlayapman" jumlasini ko'rardi.

Endi shartsiz: o'sha nuqtaga yetib kelish tool ishlaganini bildiradi
(yuqorida `if not got_function_call: return`).

### Osilib qolgan kutish xabari

Draft yiqilganda o'rniga oddiy "⏳ Javob tayyorlanmoqda..." xabari
yaratilib, unga yarim javob yoziladi. Yakuniy javob rich yo'l bilan
ketsa, o'sha yarim xabar chatda `✍️` belgisi bilan **qolib ketardi**.
Endi ishlatilmagan zaxira xabar o'chiriladi.

---

## 10. Ataylab qaytarilgan qarorlar

**Fayl kutilayotganda oraliq xabar.** Model tool'dan oldin yozgan matnni
darhol alohida xabar qilib yuborish sinab ko'rildi va **qaytarildi**
(`ad61056` → `5560bdd`). Sabab: chatda yarim chizilgan draft haqiqiy
xabar yonida qolib ketdi, tashlab ketilgan draft esa butun 1-2 daqiqalik
kutish davomida animatsiyani o'ldirdi.

Qayta urinsangiz: haqiqiy xabar yuborishdan **oldin** draft ustidan
yozilishi yoki yopilishi kerak, shunchaki yangi `draft_id` bilan
almashtirish yetarli emas.

**Manbalar slaydi.** `⛔️ MANBALAR SLAYDI YASAMANG` — URL ro'yxati
alohida slayd sifatida taqdimotni buzadi va uni AI yasaganini
oshkor qiladi. Rasm manbasi har slaydda mayda `credit=` yozuvi bilan
ko'rsatiladi.

---

## 11. Testlar

Yangi:

| Fayl | Nimani qo'riqlaydi |
|---|---|
| `test_bot_api_103.py` | 40 tekshiruv: tugmalar, nusxa matni, rasm belgilari, jadval, manbalar, to'xtatish, outcome |
| `test_deck_layout.py` | Hech bir kontent shakli kesishmasligi, rasm nisbati, altbet bandi |
| `test_file_images.py` | Hujjat rasmlari: pozitsion nomlash, kesh, JPEG ga o'girish |

Kengaytirilgan: `test_file_task_loop.py` (10/10 — sifat tekshiruvi va
fayl dublikati), `test_long_reply.py` (10/10 — osilib qolgan xabar),
`test_tool_status.py` (9/9 — fayl vazifasida faqat status),
`test_file_followup.py` (8/8 — uzun so'rovga eski fayl biriktirilmaydi).

`deck.py` ning o'z tekshiruvi: `python services/sandbox_helpers/deck.py`
(5 band — maketlar, avtomatik kichrayish, `check()` haqiqiy muammoni
topishi).

Windowsda `PYTHONIOENCODING=utf-8` bilan ishga tushiring.

---

## 12. Ochiq qolgan narsalar

- **Uzun kod uchun nusxa** — 256 belgi Bot API chegarasi. Yechim: kodni
  fayl qilib biriktirish (`_telegram_api_multipart` va `tg://document`
  infratuzilmasi tayyor) yoki Telegram'ning kod bloki ustidagi o'z
  nusxa tugmasiga tayanish.
- **Ovoz xarajati** — `gpt-4o-mini-transcribe` va `gpt-4o-mini-tts`
  bepul ro'yxatga kirmaydi va `DAILY_COUNTERS` da `voice` qatori yo'q.
- **Premium ikonka** — `icon_custom_emoji_id` faqat bot egasida Telegram
  Premium bo'lsa ko'rinadi. Sinov botida ikonkalar tushib qoladi va
  `send_rich` bezaksiz pog'onaga o'tadi (bu kod nosozligi emas).
- **`README.md` eskirgan** — `deck.py` ro'yxatda yo'q, muhit
  o'zgaruvchilarida Gemini kalitlari ko'rsatilmagan.
