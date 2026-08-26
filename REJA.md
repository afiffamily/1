# Bot API 10.3 — to'g'irlash va to'ldirish rejasi

Bu fayl `BOT_API_103.md` ning davomi emas — u **qilingan** ishni yozadi, bu esa
**qilinadigan** ishni. Har bosqich mustaqil: bittasini qilib, test qilib,
deploy qilib, keyingisiga o'tiladi. Tugagan bosqich shu yerdan o'chirilib,
`BOT_API_103.md` ga ko'chiriladi.

Manba: `https://core.telegram.org/bots/api` (10.3, 24-avgust 2026) va
aiogram `CHANGES.rst` (3.31.0, 26-avgust 2026).

Hajm belgilari: **XS** — bir necha qator · **S** — bitta fayl · **M** — 2-3 fayl
va test · **L** — yangi mexanizm.

| # | Bosqich | Hajm | Tur |
|---|---------|------|-----|
| 0 | aiogram 3.31.0 | S | poydevor |
| 1 | `image_query` ziddiyati | XS | tuzatish |
| 2 | Xabar uzunligi 4000 → 32768 | M | tuzatish |
| 3 | Rasm proaktiv chiqishi | L | tuzatish |
| 4 | `==marked==`, `<sup>`/`<sub>`, `- [ ]`, `[^1]` | M | qo'shimcha |
| 5 | `<details>` — yig'iladigan bo'lim | S | qo'shimcha |
| 6 | `<aside><cite>` — iqtibos | XS | qo'shimcha |
| 7 | `<tg-collage>` | S | qo'shimcha |
| 8 | `tg://emoji?id=` javob matnida | M | qo'shimcha |
| 9 | `<tg-map>` | L | qo'shimcha |

---

## 0. aiogram 3.29.0 → 3.31.0 · **S** · poydevor

### Nima

`main.py` dagi `stopped_message_generation` middleware hiylasi **butunlay
olib tashlanadi**. aiogram 3.31.0 (26-avgust 2026) Bot API 10.3 ni to'liq
qo'llab-quvvatlaydi:

> Added `stopped_message_generation` update and the `MessageGenerationStopped`
> type — the user stopped generation of a streamed message. **Handlers are
> registered via the new `stopped_message_generation` observer on `Router`.**

Ya'ni hozirgi izohda yozib qo'yilgan «aiogram yangilanganda bu blokni oddiy
handlerga ko'chirsa bo'ladi» — o'sha payt keldi.

### Nega

Hozirgi yechim ikkita chetlanish talab qiladi va ikkalasi ham mo'rt:

1. `dp.update.outer_middleware()` — update'ni `event_type` aniqlanishidan
   oldin ushlash, chunki `Update.event_type` bu turda `UpdateTypeLookupError`
   beradi.
2. `allowed_updates` ni **qo'lda** to'ldirish, chunki handler yo'q va aiogram
   uni ro'yxatdan chiqara olmaydi.

Handler bo'lgach ikkalasi ham keraksiz: `resolve_used_update_types()` update
turini o'zi topadi.

### Fayllar

- `requirements.txt:17`
- `main.py:71-96` (middleware), `main.py:231-239` (allowed_updates)
- `tests/test_bot_api_103.py` — 22-tekshiruv

### Qadamlar

1. `requirements.txt`: `aiogram==3.29.0` → `aiogram==3.31.0`. Izohni
   yangilash — hozir «Guest Mode uchun >= 3.29 shart» deb turibdi, endi
   «Bot API 10.3 (stopped_message_generation observer) uchun >= 3.31».
2. `main.py`: middleware o'rniga

   ```python
   @dp.stopped_message_generation()
   async def on_generation_stopped(event: MessageGenerationStopped):
       if not messages_module.request_stop(event.draft_id):
           logger.debug(...)
   ```

   Ro'yxatga olish tartibi muhim emas — bu alohida observer, `dp.message`
   zanjiriga umuman tegmaydi.
3. `main.py:236-238` — qo'lda qo'shish blokini o'chirish,
   `await dp.start_polling(bot, allowed_updates=dp.resolve_used_update_types())`
   qoldirish.
4. `handlers/messages.py:request_stop()` — **tegilmaydi**, u o'z holicha to'g'ri.

### Xavf

3.29 → 3.31 orasida bizga tegishli breaking change **yo'q** (changelog
tekshirildi: faqat bugfix va yangi Bot API turlari). Lekin 3.30.0 da
`ephemeral_message_parameters` bo'yicha tuzatish bor — bizning
`ephemeral_params()` xom dict qaytaradi va `pro_module.send_rich` orqali
ketadi, ya'ni ta'sir qilmaydi. Shunga qaramay `/pro` va guruh javoblarini
deploydan keyin bir marta qo'lda tekshirish kerak.

### Test

- `tests/test_bot_api_103.py` 22-tekshiruv (`noma'lum draft uchun
  request_stop False qaytaradi`) — o'zgarishsiz o'tishi kerak.
- Yangi tekshiruv: `dp.resolve_used_update_types()` ichida
  `stopped_message_generation` **bor**ligi. Bu qo'lda qo'shishni olib
  tashlaganimiz xavfsiz ekanini isbotlaydi.
- Deploydan keyin jonli: uzun javob so'rab, to'xtatish tugmasini bosish.

### Keyin ochiladigan imkoniyat (shu bosqichda QILINMAYDI)

3.31.0 da `SendRichMessage`, `SendRichMessageDraft`, `InputRichBlock*`
turlari bor. Ya'ni `_telegram_api_request` orqali xom HTTP so'rov o'rniga
aiogram metodlarini ishlatsa bo'ladi. **Hozircha ko'chirilmaydi**: bizning
xom yo'lda `outcome` (REJECTED / UNKNOWN farqi) va `RICH_MEDIA_TIMEOUT`
mantiqi bor, aiogram esa ikkalasini ham bermaydi. Buni alohida bosqich
sifatida keyin ko'rib chiqamiz.

---

## 1. `image_query` tavsifi kod bilan ziddiyatda · **XS** · tuzatish

### Nima

Tool tavsifi modelga aytadi:

> Bezak so'zlarini (`'classic'`, `'chiroyli'`, **`'2024'`**, `'narxi'`) QO'SHMANG

Lekin `image_query()` endi **yilni ataylab saqlaydi** — «Hongqi H5 2025» va
«Hongqi H5» boshqa mashina bo'lgani uchun. Kod bir narsa qiladi, prompt
boshqasini aytadi.

### Nega

Foydalanuvchi «yangi modelining rasmini ber» deganda ajratuvchi belgi aynan
yil bo'ladi. Model uni yozmasa, kodning yilni saqlashi hech qachon
ishlamaydi — saqlaydigan yil yo'q.

### Fayllar

- `services/ai.py` — `image_query` parametr tavsifi

### Qadamlar

Taqiqlangan so'zlar ro'yxatidan `'2024'` ni olib tashlash va bitta qator
qo'shish:

> YIL — bezak emas, agar u modelni ajratsa: «Hongqi H5 2025», «iPhone 17».
> Umumiy mavzuda («Samarqand Registan») yil YOZMANG.

`'classic'`, `'chiroyli'`, `'narxi'` ro'yxatda qoladi — ular haqiqatan
Commons qidiruvini buzadi.

### Test

`tests/test_bot_api_103.py` 14a allaqachon yilni saqlashni tekshiradi.
Qo'shimcha test shart emas — bu faqat matn.

---

## 2. Xabar uzunligi: 4000 → 32768 · **M** · tuzatish

### Nima

`handlers/messages.py:234-237`:

```python
# Telegram bitta xabarga 4096 belgi ruxsat beradi. 4000 — zaxira bilan
MAX_MESSAGE_CHARS = 4000
```

Bu `sendMessage` chegarasi. Hujjatning **Rich Message Limits** bo'limi:

> Up to **32768** UTF-8 characters in the rich message text, including custom
> emoji alternative text and formula source.
> Up to 500 blocks · 16 levels of nesting · 50 media · 20 columns

### Nega

Hozir 9000 belgilik javob **uchta** rich xabarga bo'linayapti, bittada
ketishi mumkin bo'lgani holda. Va har bir bo'linish — xavf: kod bloki
yopilib qayta ochiladi, markdown havolasi kesilib qolishi mumkin
(`• [OLX` / `Uzbekistan](https://…)` nosozligi aynan shundan chiqqan).
Bo'linish qancha kam bo'lsa, o'sha xavf shuncha kam.

### Fayllar

- `handlers/messages.py` — `MAX_MESSAGE_CHARS`, `_split_for_telegram()`,
  `process_stream_draft()` ning yakuniy yuborish sikli
- `tests/test_long_reply.py` — 1, 3, 6, 11-tekshiruvlar

### Qadamlar

1. Ikkita chegara: `MAX_RICH_CHARS = 30000` (32768 dan zaxira bilan — 
   `build_rich_markdown()` matnga `<tg-math>`, `<tg-time>`, `<table>`
   teglari qo'shib uzunlikni oshiradi) va `MAX_PLAIN_CHARS = 4000`.
2. `_split_for_telegram(text, limit)` — imzosi allaqachon `limit` oladi,
   o'zgartirish shart emas.
3. `process_stream_draft()`: bo'lish `can_send_rich` ga qarab tanlanadi.
4. **⚠️ ENG MUHIM QISM.** Hozirgi pog'ona shunday ishlaydi: rich rad
   etilsa, o'sha bo'lak oddiy xabar sifatida yuboriladi. 30000 belgilik
   bo'lakni oddiy xabar sifatida yuborib bo'lmaydi — Telegram 4096 da
   kesadi. Ya'ni zaxira yo'liga tushganda bo'lak **qayta bo'linishi**
   kerak:

   ```python
   for kichik in _split_for_telegram(part, MAX_PLAIN_CHARS):
       await _answer_plain(message, strip_image_tokens(kichik))
   ```

   Busiz tuzatish javobni **yo'qotadi** — hozirgi holatdan yomonroq.
5. Draft (`sendRichMessageDraft`) ham rich xabar, ya'ni unga ham 32768
   tegishli. Hozir draft matni kesilmaydi — 30000 dan oshsa kesish
   qo'shilishi kerak (uzun javobda draft rad etilib, spinner o'chib
   qolmasligi uchun).

### Xavf

Yagona jiddiy xavf 4-qadamda: zaxira yo'lida qayta bo'lish unutilsa,
rich rad etilgan uzun javob **butunlay yo'qoladi**.
`tests/test_long_reply.py` 5-tekshiruvi aynan shuni qo'riqlaydi.

### Test

- 6-tekshiruv o'zgaradi: 9000 belgi endi **1 ta** rich xabar.
- Yangi tekshiruv: 40000 belgilik javob → 2 ta rich xabar.
- Yangi tekshiruv: rich rad etilganda 30000 belgilik javob 4096 dan
  kichik bo'laklarda **to'liq** yetib borishi (5-tekshiruvning uzun
  varianti).

---

## 3. Rasm proaktiv chiqishi · **L** · tuzatish

### Nima

Bot rasmni **faqat** foydalanuvchi «rasm» so'zini aytganda yuboradi.
Kerakli paytni o'zi hisoblab chiqarmaydi. Bu Bot API bilan bog'liq emas —
sabab ikkita, ikkalasi ham bizning kodda.

### Sabab a — tool tavsifi «yo'q» tomonga og'gan

`services/ai.py`, `want_images` tavsifining oxiri:

> false QOLDIRING: valyuta kursi, ob-havo, yangilik matni, narx, statistika,
> **ta'rif, tarix**, maslahat, kod, hisob-kitob…
> **Shubhalansangiz false qiling**: keraksiz rasm javobni og'irlashtiradi.

Model deyarli har doim shubhalanadi. Va «tarix» bilan «ta'rif» — aynan rasm
eng ko'p yordam beradigan mavzular (tarixiy voqea, bino, hayvon, asbob),
lekin ular *false* ro'yxatida turibdi.

### Sabab b — rasm veb-qidiruvga MAHKAM bog'langan (kattaroq muammo)

Rasm faqat `internet_search` chaqirilganda topiladi. Model savolga o'z
bilimidan javob bersa — qidiruvni umuman chaqirmaydi — rasm chiqishi
**jismonan mumkin emas**.

«Eyfel minorasi haqida ayt», «tulki qanday hayvon», «Amir Temur kim edi» —
bularning hech biriga model qidirmaydi, demak hech qachon rasm ham
bo'lmaydi. Malibu so'rovida rasm chiqqani faqat u haqda qidiruv bo'lgani
uchun.

### Fayllar

- `services/ai.py` — `want_images` va `image_query` tavsiflari,
  `internet_search` sxemasi, tool dispatch (`else` shoxi)
- `core/config.py` — `IMAGE_CAPABILITY_NOTE`
- `tests/test_search_images_loop.py`

### Qadamlar

**3a. Tavsifni qayta yozish (XS).** «Shubhalansangiz false qiling» olib
tashlanadi. Ro'yxatlar almashadi:

- *true*: ko'z bilan ko'riladigan har qanday narsa — mahsulot, jonzot,
  o'simlik, taom, joy, bino, shaxs, asar, asbob, hodisa, tarixiy voqea.
- *false*: mavhum tushuncha (iqtisodiyot, motivatsiya, strategiya), raqam
  va hisob (kurs, ob-havo, statistika), kod, matematika, maslahat, tarjima.
- Shubhalanish qoidasi teskari: **mavzuning aniq ko'rinishi bo'lsa —
  true**.

**3b. Rasmni qidiruvdan ajratish (M).** `internet_search` ga yangi
ixtiyoriy `images_only: boolean` parametri qo'shiladi. `true` bo'lsa
`multi_source_deep_search()` **umuman chaqirilmaydi** — faqat
`search_images()` ishlaydi va katalog qaytadi.

Nega alohida tool emas: yangi tool sxemasi har bir so'rovda modelga
yuboriladi, ya'ni hamma foydalanuvchi uchun doimiy token xarajati. Mavjud
toolga bitta boolean qo'shish deyarli tekin.

Nega tez: hozir rasm uchun 3 ta so'rov + 3 ta sahifa yuklanadi (~5-10s va
~5 ming token). `images_only=true` da faqat Commons API — 1 soniya, nol
token.

Dispatch shoxi (`else`) shunday bo'ladi:

```python
if args.get("images_only"):
    tool_output = ""          # veb natijasi yo'q
else:
    tool_output = await multi_source_deep_search(...)
# rasm qismi o'zgarishsiz
```

⚠️ `search_rounds` byudjeti `images_only` chaqiruviga ham hisoblanadi —
aks holda model cheksiz rasm so'rab tura oladi.

**3c. `IMAGE_CAPABILITY_NOTE` (XS).** Hozir u faqat «yubora olasiz» deydi.
Qo'shiladi: qaror modelning o'zida, foydalanuvchi so'rashi shart emas; va
qidiruv kerak bo'lmasa `images_only=true` ishlatilishi.

### Xavf

Rasm chiqishi ko'payadi, demak:

- Har bir rasmli xabar Telegram tomonidan sekinroq yaratiladi
  (`RICH_MEDIA_TIMEOUT` allaqachon bor, lekin yuk oshadi).
- Commons aloqasiz rasm bermaydi (`_image_relevant()` qo'riqlaydi), lekin
  «mos rasm topilmadi» holati ko'payadi — bu normal, rasm shunchaki
  qo'yilmaydi.
- Kutilmagan joyda rasm chiqib qolishi mumkin. Shuning uchun 3a dagi
  *false* ro'yxati aniq bo'lishi kerak.

### Test

- `images_only=true` da `multi_source_deep_search` **chaqirilmasligi**.
- `images_only=true` da ham katalog qaytishi.
- `images_only` chaqiruvi `search_rounds` byudjetini yeyishi.

---

## 4. `==marked==`, `<sup>`/`<sub>`, `- [ ]`, `[^1]` · **M** · qo'shimcha

### Nima

10.3 rich markdown to'rtta konstruktsiyani beradi, biz hech birini
ishlatmaymiz:

| Sintaksis | Ko'rinishi | Qayerda kerak |
|-----------|-----------|---------------|
| `==matn==` | sariq marker | javobning eng muhim jumlasi |
| `<sup>`/`<sub>` | yuqori/quyi indeks | H<sub>2</sub>O, m<sup>2</sup>, x<sup>n</sup> |
| `- [ ]` / `- [x]` | belgilanadigan ro'yxat | reja, bosqichlar, tekshiruv ro'yxati |
| `[^1]` + `[^1]: ...` | haqiqiy izoh | manbani jumlaga bog'lash |

### Nega

Bularning uchtasi **faqat prompt** masalasi — model markdown yozadi,
Telegram o'zi chizadi, kodda hech narsa qilish shart emas. Faqat izoh
(`[^1]`) kodga tegadi.

### Fayllar

- `core/config.py` — system prompt (formatlash qoidalari)
- `handlers/messages.py` — `_safe_cut()`, `_protect_spans()` tekshiruvi
- `tests/test_long_reply.py`, `tests/test_rich_markdown.py`

### Qadamlar

1. System promptga qisqa ro'yxat qo'shish: qachon `==` (javobda ko'pi
   bilan bitta jumla), qachon `<sub>`/`<sup>` (kimyo formulalari va
   daraja — LaTeX `$...$` **o'rniga emas**, uning yonida: matn ichidagi
   H₂O uchun), qachon `- [ ]` (bosqichli reja).
2. **⚠️ `[^1]` bo'linishga chidamsiz.** Izoh ta'rifi (`[^1]: ...`) javob
   OXIRIDA turadi. `_split_for_telegram()` javobni bo'lsa, ta'rif
   ikkinchi xabarga tushib qoladi va birinchi xabardagi `[^1]` havolasi
   **hech qayerga olib bormaydi**. Ikki yo'l bor:
   - a) 2-bosqichdan keyin bo'linish kamayadi, lekin yo'qolmaydi —
     shuning uchun `_safe_cut()` ga qoida: izoh ta'riflari boshlangan
     joydan keyin kesilmasin;
   - b) yoki soddaroq: bo'linish bo'lsa izohlar oddiy matnga aylantirilsin.
   **Tavsiya: (a)** — kod bloki va markdown havolasi uchun allaqachon
   shunday qilingan, uchinchi qoida o'sha joyga tushadi.
3. `==` belgisi kod bloki ichida bo'lishi mumkin (`x == y`) —
   `_protect_spans()` allaqachon kod bloklarini himoyalaydi, tekshirib
   tasdiqlash kerak.

### Test

- `==` kod bloki ichida saqlanishi.
- Izoh havolasi va ta'rifi bir xabarda qolishi.

---

## 5. `<details>` — yig'iladigan bo'lim · **S** · qo'shimcha

### Nima

```html
<details open><summary>Sarlavha</summary>
Mazmun (markdown parslanadi)
</details>
```

Hujjat aniq aytadi: markdown faqat `<details>`, `<tg-collage>` va
`<tg-slideshow>` ichida parslanadi. Ya'ni `<details>` ichida oddiy
markdown yozish mumkin.

### Nega

Hozir yig'iladigan blok faqat manbalar uchun ishlatiladi
(`_collapse_sources`, `<blockquote expandable>`). Uzun javobda esa
«batafsil», «texnik xususiyatlar», «to'liq jadval» kabi bo'limlar bor —
ular ekranni to'ldiradi, lekin hammaga kerak emas.

### Fayllar

- `core/config.py` — system prompt
- `services/ai.py` — `build_rich_markdown()`

### Qadamlar

Ikki yondashuv bor:

- **Model o'zi yozadi.** Promptga: «ikkilamchi tafsilot (to'liq jadval,
  texnik xususiyatlar ro'yxati, uzun sitata) `<details>` ichiga».
  Oddiy, lekin model buni tez-tez unutadi yoki aksincha, hamma joyga
  qo'yadi.
- **Belgi orqali.** Model `[batafsil: Sarlavha]` … `[/batafsil]` yozadi,
  `build_rich_markdown()` uni `<details>` ga o'giradi.
  Ishonchliroq, chunki noto'g'ri yozilgan belgi shunchaki tashlanadi va
  xabar rad etilmaydi.

**Tavsiya: belgi orqali** — `[rasm:N]` bilan bir xil tamoyil, va u
ishlayotgani isbotlangan.

### Xavf

`<details>` ichida `<table>` yoki media blok bo'lsa — hujjat 500 blok va
16 daraja ichma-ichlik chegarasini qo'yadi. Bizning javoblar bunga
yaqinlashmaydi, lekin `<details>` ichiga `<details>` qo'yilmasligini
ta'minlash kerak.

### Test

Belgi `<details>` ga o'girilishi; yopilmagan belgi xabarni buzmasligi.

---

## 6. `<aside><cite>` — iqtibos · **XS** · qo'shimcha

### Nima

```html
<aside>Iqtibos matni<cite>Muallif</cite></aside>
```

Matndan ajralib turadigan katta iqtibos (pull quote).

### Nega

Tarixiy shaxs, kitob, nutq haqidagi javoblarda iqtibos hozir oddiy
`>` blok sifatida ketadi — manbadan ajralmaydi.

### Fayllar

- `core/config.py` — system prompt
- `services/ai.py` — `build_rich_markdown()`

### Qadamlar

5-bosqich bilan **bir xil mexanizm**: `[iqtibos: matn | muallif]` belgisi
→ `<aside>`. Shuning uchun 5-bosqichdan keyin qilinsa, kod deyarli
takrorlanmaydi — bitta umumiy belgi o'giruvchi yetadi.

### Test

Belgi to'g'ri o'girilishi; muallifsiz variant ham ishlashi.

---

## 7. `<tg-collage>` · **S** · qo'shimcha

### Nima

Hozir 2+ rasm doim `<tg-slideshow>` ga tushadi — foydalanuvchi rasmlarni
**surib** ko'radi. `<tg-collage>` esa hammasini bir ekranda ko'rsatadi.

### Nega

2-4 rasm uchun kollaj yaxshiroq: bir qarashda hammasi ko'rinadi.
Slideshow 5+ rasmda o'z o'rniga ega — kollaj ularni juda mayda qiladi.

### Fayllar

- `services/ai.py` — `embed_images()`, `_image_block()`
- `core/config.py` — yangi `SEARCH_IMAGE_COLLAGE_MAX = 4`
- `tests/test_bot_api_103.py` — 12-tekshiruv

### Qadamlar

`embed_images()` dagi `gallery()` funksiyasi:

- 1 ta rasm → hozirgidek yakka media blok;
- 2…`SEARCH_IMAGE_COLLAGE_MAX` ta → `<tg-collage>`;
- undan ko'p → `<tg-slideshow>` (hozirgidek).

Ichki tuzilma bir xil — hujjat kollaj ichida ham markdown parslanishini
tasdiqlaydi, ya'ni `_image_block()` o'zgarmaydi.

### Xavf

Kollajda sarlavha (`figcaption`) bitta — har bir rasmning alohida
manbasini ko'rsatib bo'lmaydi. Rasm manbasi bizda **majburiy** (rasm
o'zganiki). Yechim: kollaj sarlavhasiga barcha manbalar vergul bilan.
Buni oldindan hal qilmasdan kodni yozmaslik kerak.

### Test

2 rasm → collage, 5 rasm → slideshow, 1 rasm → yakka blok.

---

## 8. `tg://emoji?id=` javob matnida · **M** · qo'shimcha

### Nima

Markdown sintaksisi (hujjatdan, **bo'sh joy alt matnida — shart**):

```
![ ](tg://emoji?id=5368324170671202286)
```

### Nega

`CUSTOM_EMOJI` lug'ati `core/config.py` da allaqachon bor va ishlatilyapti,
lekin faqat ikki joyda: draft ichidagi `<tg-thinking>` va tugma ikonkasi
(`icon_custom_emoji_id`). **Javob matnining o'zida** premium emoji hech
qachon chiqmaydi.

### Fayllar

- `core/config.py` — `CUSTOM_EMOJI`
- `services/ai.py` — `build_rich_markdown()`
- `tests/test_rich_markdown.py`

### Qadamlar

1. `build_rich_markdown()` ga bosqich qo'shish: javobdagi ma'lum emojilar
   (🤖 📄 🧠 ⏰ 🧹 ✍️ — `CUSTOM_EMOJI` da ID'si borlari) animatsion
   variantiga almashtiriladi.
2. **⚠️ Faqat kod bloklaridan tashqarida.** `_protect_spans()` dan keyin
   ishlashi shart.
3. **⚠️ Alt matnda bo'sh joy bo'lishi shart** — `![ ](...)`, `![](...)`
   emas. Hujjatdagi misol aynan shunday va bu tasodif emas: bo'sh alt
   media blok sifatida o'qilishi mumkin.
4. Chegara: hujjat «custom emoji alternative text» ni 32768 belgi hisobiga
   qo'shadi. Har bir almashtirish ~40 belgi qo'shadi, ya'ni javobda
   ko'pi bilan 10-15 ta almashtirish.

### Xavf

Premium sharti: hujjat `icon_custom_emoji_id` uchun «bot egasida Telegram
Premium bo'lsa» deydi. Matn ichidagi custom emoji uchun ham shu shart
amal qiladi. Bizda draft'da `<tg-emoji>` allaqachon ishlayapti, ya'ni
shart bajarilgan — lekin obuna tugasa **butun xabar rad etilishi**
mumkin. Shuning uchun rad etilganda emojisiz qayta yuborish pog'onasi
kerak (`plain_md` ga o'xshab).

### Test

Kod bloki ichidagi emoji tegilmasligi; almashtirilgan emoji `![ ](` 
shaklida (bo'sh joy bilan) chiqishi.

---

## 9. `<tg-map>` · **L** · qo'shimcha

### Nima

```html
<tg-map lat="41.9" long="12.5" zoom="14"/>
<figure><tg-map lat="41.9" long="12.5" zoom="14"/><figcaption>Izoh</figcaption></figure>
```

Xabar ichiga interaktiv xarita chizadi. Hozir bu imkoniyat **mutlaqo**
ishlatilmagan.

### Nega

«Samarqand qayerda», «Bu restoran qayerda joylashgan», «Verdun jangi qayerda
bo'lgan», sayohat rejasi — bularning hammasida xarita rasmdan ham
foydaliroq. Va bu Telegram'ga XOS imkoniyat: veb-chatbot xarita chiza
olmaydi.

### Fayllar

- `services/ai.py` — yangi belgi va o'giruvchi, tool yoki prompt
- `core/config.py` — system prompt
- yangi test fayli

### Qadamlar

Koordinata qayerdan keladi — asosiy savol. Uch variant:

- **a) Model o'zi yozadi.** Mashhur joylarning koordinatasini model yaxshi
   biladi. Belgi: `[xarita:41.3111,69.2797,12]`. Kod uni tekshiradi
   (lat −90…90, long −180…180, zoom 1…20) va `<tg-map>` ga o'giradi.
   Noto'g'ri bo'lsa belgi shunchaki o'chiriladi — `[rasm:N]` bilan bir xil
   tamoyil.
- **b) Geokodlash.** Nominatim/Wikidata orqali nom bo'yicha koordinata
   olish. Aniqroq, lekin yana bitta tarmoq so'rovi, yana bitta rate limit,
   yana bitta buzilish nuqtasi.
- **c) Ikkalasi.** Model yozgan koordinata shubhali bo'lsa geokodlash.

**Tavsiya: (a)** — eng arzon va eng kam buzilish nuqtasi. Model xato
koordinata yozsa xarita noto'g'ri joyni ko'rsatadi, lekin bu «rasm
chiqmadi» darajasidagi nosozlik, javobni buzmaydi. (b) ni keyin qo'shsa
bo'ladi.

⚠️ Noto'g'ri koordinatani **tekshirib bo'lmaydi** — 41.9/12.5 Rim,
41.3/69.3 Toshkent, ikkalasi ham «to'g'ri ko'rinadi». Shuning uchun
promptda qat'iy shart: koordinatani faqat **aniq bilgan** joy uchun
yozsin, shubhalansa umuman yozmasin.

### Xavf

- Xarita blok — media, ya'ni 50 ta media chegarasiga kiradi (bizga uzoq).
- `<tg-map/>` — yopiluvchi teg, `<tg-map></tg-map>` emas. Noto'g'ri
  yozilsa butun xabar rad etiladi.
- Zoom qiymati: 14 — shahar ko'chasi, 5 — mamlakat. Model buni bilmaydi,
  promptda misol berish kerak.

### Test

To'g'ri belgi → `<tg-map/>`; chegaradan tashqari koordinata → belgi
o'chirilishi; belgi kod bloki ichida tegilmasligi.

---

## Tartib haqida

Tavsiya etilgan ketma-ketlik yuqoridagi jadval tartibida:

1. **0** birinchi — u kodni soddalashtiradi va keyingi ishlarni osonlashtiradi.
2. **1, 2, 3** — tuzatishlar, ya'ni hozir buzuq bo'lgan narsa. 3-bosqich
   sizning asosiy shikoyatingiz.
3. **4-9** — qo'shimchalar. Bular orasida 4, 5, 6 bir-biriga yaqin (bitta
   belgi o'giruvchi mexanizm), shuning uchun ketma-ket qilingani ma'qul.
4. **9** eng oxirida — eng katta va eng ko'p noaniqligi bor.

Har bosqichdan keyin: butun test to'plami → commit → Railway deploy →
jonli tekshiruv. Bittasi buzilsa, oldingi bosqichlar tegilmagan bo'ladi.
