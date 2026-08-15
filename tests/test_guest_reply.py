"""Guest rejimda reply qilingan xabar konteksti.
Ishga tushirish: python tests/test_guest_reply.py

NEGA KERAK: guruhda bot a'zo emas va tarixni ko'rmaydi. Reply qilingan
xabar — botga yetib boradigan YAGONA kontekst. U yo'qolsa, foydalanuvchi
savolga reply qilib botni chaqirganda bot "nima haqida gap ketyapti?" deb
so'raydi va Guest Mode'ning eng tabiiy ishlatilishi buziladi.
"""

import os
import sys
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from handlers.guest import (
    _quoted_context, _media_source, _detect_guest_content_type, _QUOTE_MAX_CHARS,
)


class FakeUser:
    def __init__(self, full_name, is_bot=False):
        self.full_name = full_name
        self.is_bot = is_bot


class FakeMsg:
    def __init__(self, text=None, caption=None, from_user=None,
                 reply_to_message=None, quote=None,
                 photo=None, document=None, voice=None):
        self.text = text
        self.caption = caption
        self.from_user = from_user
        self.reply_to_message = reply_to_message
        self.quote = quote
        self.photo = photo
        self.document = document
        self.voice = voice


class FakeQuote:
    def __init__(self, text):
        self.text = text


def main():
    aziz = FakeUser("Aziz Karimov")

    # ── 1) Reply yo'q — kontekst ham yo'q ────────────────────────────
    assert _quoted_context(FakeMsg(text="@bot salom")) == ""
    print("[1] reply yo'q bo'lsa bo'sh qaytadi OK")

    # ── 2) Oddiy reply: matn ham, muallif ham kontekstga tushadi ─────
    m = FakeMsg(text="@bot", reply_to_message=FakeMsg(
        text="Python'da list va tuple farqi nima?", from_user=aziz))
    ctx = _quoted_context(m)
    assert "Aziz Karimov" in ctx, ctx
    assert "list va tuple" in ctx, ctx
    print("[2] reply qilingan savol matni va muallifi olindi OK")

    # ── 3) Caption ham matn sifatida qabul qilinadi ──────────────────
    m = FakeMsg(text="@bot", reply_to_message=FakeMsg(
        caption="Bu grafikni tushuntiring", from_user=aziz))
    assert "grafikni" in _quoted_context(m)
    print("[3] rasm/hujjat caption'i kontekstga tushdi OK")

    # ── 4) Belgilangan bo'lak (quote) butun xabardan USTUN ───────────
    # Uzun xabardan foydalanuvchi aynan bitta jumlani ajratgan bo'lsa,
    # savol o'sha jumla haqida — qolgani shovqin.
    m = FakeMsg(text="@bot", quote=FakeQuote("faqat shu jumla"),
                reply_to_message=FakeMsg(text="juda uzun matn " * 50,
                                         from_user=aziz))
    ctx = _quoted_context(m)
    assert "faqat shu jumla" in ctx, ctx
    assert "juda uzun matn" not in ctx, "belgilangan bo'lak ustun turishi kerak"
    print("[4] belgilangan bo'lak butun xabardan ustun OK")

    # ── 5) Bo'sh/matnsiz reply (masalan stiker) kontekst bermaydi ────
    assert _quoted_context(FakeMsg(text="@bot", reply_to_message=FakeMsg(
        from_user=aziz))) == ""
    assert _quoted_context(FakeMsg(text="@bot", reply_to_message=FakeMsg(
        text="   ", from_user=aziz))) == ""
    print("[5] matnsiz reply kontekst bermadi OK")

    # ── 6) Bot o'z xabariga reply — "Bot" deb belgilanadi ────────────
    m = FakeMsg(text="@bot davom et", reply_to_message=FakeMsg(
        text="Javob shu edi", from_user=FakeUser("AI Bot", is_bot=True)))
    assert _quoted_context(m).startswith("Bot yozgan"), _quoted_context(m)
    print("[6] botning o'z xabari 'Bot' deb belgilandi OK")

    # ═══════════════════════════════════════════════════════════════
    # 7) UZUN XABAR KESILADI — aks holda bitta forward qilingan uzun
    #    matn butun kunlik token limitini yeb qo'yishi mumkin.
    # ═══════════════════════════════════════════════════════════════
    m = FakeMsg(text="@bot", reply_to_message=FakeMsg(
        text="q" * 50000, from_user=aziz))
    ctx = _quoted_context(m)
    assert ctx.count("q") == _QUOTE_MAX_CHARS, ctx.count("q")
    print(f"[7] {_QUOTE_MAX_CHARS} belgidan uzun xabar kesildi OK")

    # ── 8) Muallifi noma'lum (anonim admin) yiqilmaydi ──────────────
    m = FakeMsg(text="@bot", reply_to_message=FakeMsg(text="Savol", from_user=None))
    assert "Kimdir" in _quoted_context(m)
    print("[8] anonim muallifda yiqilmadi OK")

    # ═══════════════════════════════════════════════════════════════
    # 9) MEDIA REPLY'DAN OLINADI — rasm/hujjat/ovozga reply qilib
    #    savol berilganda bot o'sha faylni ISHLATISHI kerak. Aks holda
    #    ko'rmagan rasm haqida taxmin qilib javob berardi.
    #    Bu content_type'ni ham belgilaydi, ya'ni KUNLIK LIMIT ham
    #    to'g'ri turdagi narx bilan yechiladi (matn emas, rasm narxi).
    # ═══════════════════════════════════════════════════════════════
    for kind in ("photo", "document", "voice"):
        src = FakeMsg(from_user=aziz, **{kind: object() if kind != "photo" else ["p"]})
        caller = FakeMsg(text="@bot bu nima?", reply_to_message=src)
        assert _media_source(caller) is src, kind
        assert _detect_guest_content_type(_media_source(caller)) == kind, kind
    print("[9] rasm/hujjat/ovozga reply → media reply'dan olindi OK")

    # ── 10) O'z medias'i reply'dan USTUN ────────────────────────────
    # O'zi yangi rasm yuborib, eski rasmga reply qilgan bo'lsa —
    # savol YANGI rasm haqida.
    own = FakeMsg(text="@bot", photo=["yangi"],
                  reply_to_message=FakeMsg(photo=["eski"], from_user=aziz))
    assert _media_source(own) is own
    print("[10] chaqiruvchining o'z rasmi reply'dan ustun turdi OK")

    # ── 11) Media'siz reply content_type'ni o'zgartirmaydi ──────────
    m = FakeMsg(text="@bot", reply_to_message=FakeMsg(text="oddiy savol", from_user=aziz))
    assert _detect_guest_content_type(_media_source(m)) == "text"
    print("[11] matnli reply matn bo'lib qoldi (limit matn narxida) OK")

    print("\nguest reply: barcha tekshiruvlar o'tdi (11/11).")


if __name__ == "__main__":
    main()
