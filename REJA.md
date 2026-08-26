# Bot API 10.3 — to'g'irlash va to'ldirish rejasi

**Reja to'liq bajarildi. Bajarilmagan bosqich qolmadi.**

O'nta bosqich ham (0-9) shu yerdan olinib, `BOT_API_103.md` ga —
qilingan ishni yozadigan faylga — ko'chirildi:

| # | Bosqich | Qayerda yozilgan |
|---|---------|------------------|
| 0 | aiogram 3.31.0, `stopped_message_generation` observer'i | 2-bo'lim |
| 1 | `image_query` tavsifidagi yil ziddiyati | 5-bo'lim |
| 2 | Xabar uzunligi 4000 → 30000/4000 | 1-bo'lim |
| 3 | Rasm proaktiv chiqishi, `images_only` | 5-bo'lim |
| 4 | `==marked==`, `<sup>`/`<sub>`, `- [ ]`, `[^1]` | 1-bo'lim |
| 5 | `<details>` — yig'iladigan bo'lim | 1-bo'lim |
| 6 | `<aside><cite>` — iqtibos | 1-bo'lim |
| 7 | `<tg-collage>` | 5-bo'lim |
| 8 | `tg://emoji?id=` javob matnida | 1-bo'lim |
| 9 | `<tg-map>` | 1-bo'lim |

Yangi reja tug'ilsa shu fayl qayta ishlatiladi; bo'lmasa uni o'chirib
tashlash mumkin.

⚠️ Jonli tekshirish HALI QILINMAGAN. Deploydan keyin bir marta qo'lda
ko'rish kerak bo'lgan narsalar:

- to'xtatish tugmasi (uzun javob so'rab, tugmani bosish);
- `/pro` va guruhdagi javob (aiogram 3.30 dagi `ephemeral` tuzatishi);
- «Eyfel minorasi haqida ayt» — rasm bilan kelishi, «dollar kursi» —
  rasmsiz;
- «Hongqi H5 2025 rasmini ber» — yil saqlanishi;
- yig'iladigan bo'lim, iqtibos, xarita va premium emoji chiqishi
  (ular model belgini YOZISHIGA bog'liq, kod tomoni test bilan
  qoplangan).
