"""«Nima qila olaman?» ekrani va jimlik o'rniga javob.
Ishga tushirish: python tests/test_capabilities.py

ENG MUHIM TEKSHIRUVLAR:
  4-band — qo'llab-quvvatlanmagan tur (video, stiker, audio) JAVOBSIZ
    qolmasligi. Ilgari bunday xabar uchun handler umuman yo'q edi va bot
    mutlaqo jim qolardi — foydalanuvchi uchun bu "bot o'ldi" degani.
  6-band — tugma stillari FAQAT primary/success/danger bo'lishi. Boshqa
    qiymatni Telegram rad etadi va BUTUN xabar yuborilmaydi, ya'ni ekran
    umuman ochilmaydi (core/config.py izohi).
"""

import os
import sys
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
import asyncio

from handlers import capabilities as cap
from core.config import BTN_PRIMARY, BTN_SUCCESS, BTN_DANGER


class FakeMessage:
    """send_rich() va edit_text() ni kuzatadigan soxta xabar."""
    def __init__(self, edit_ok=True):
        self.edit_ok = edit_ok
        self.sent = []      # (matn, klaviatura)
        self.edited = []

    async def answer(self, text, **kwargs):
        self.sent.append((text, kwargs.get("reply_markup")))
        return self

    async def edit_text(self, text, **kwargs):
        if not self.edit_ok:
            raise RuntimeError("message is not modified")
        self.edited.append((text, kwargs.get("reply_markup")))
        return self


class FakeQuery:
    def __init__(self, data, message):
        self.data = data
        self.message = message
        self.answered = False

    async def answer(self, *a, **k):
        self.answered = True


def _all_buttons(kb):
    return [b for row in kb.inline_keyboard for b in row]


async def main():
    # ── 1) Asosiy ekran: har bo'lim uchun tugma bor ─────────────────
    msg = FakeMessage()
    await cap.handle_help(msg)
    assert len(msg.sent) == 1, msg.sent
    text, kb = msg.sent[0]
    assert "NIMA QILA OLAMAN" in text, text
    keys = {b.callback_data for b in _all_buttons(kb)}
    assert keys == {f"cap:{k}" for k in cap.SECTIONS}, keys
    print(f"[1] /help ekrani {len(keys)} ta bo'lim tugmasi bilan ochildi OK")

    # ── 2) Har bir bo'lim ochiladi va "Orqaga" tugmasi bor ──────────
    for key in cap.SECTIONS:
        m = FakeMessage()
        q = FakeQuery(f"cap:{key}", m)
        await cap.handle_capabilities_callback(q)
        assert q.answered, "callback javobsiz qolsa Telegram'da soat aylanaveradi"
        assert m.edited, f"{key}: ekran tahrirlanishi kerak"
        body, kb = m.edited[0]
        assert cap.SECTIONS[key]["title"] in body, key
        assert "cap:menu" in {b.callback_data for b in _all_buttons(kb)}, (
            f"{key}: 'Orqaga' tugmasi yo'q — foydalanuvchi tuzoqda qoladi")
    print(f"[2] {len(cap.SECTIONS)} ta bo'lim ochildi, hammasida 'Orqaga' bor OK")

    # ── 3) Misollar <code> ichida (bosib nusxalash uchun) ───────────
    with_example = [k for k, s in cap.SECTIONS.items() if s["example"]]
    assert len(with_example) >= 4, with_example
    for key in with_example:
        body = cap._section_text(key)
        assert f"<code>{cap.SECTIONS[key]['example']}</code>" in body, key
    print(f"[3] {len(with_example)} ta bo'limda nusxalanadigan misol bor OK")

    # ═══════════════════════════════════════════════════════════════
    # 4) QO'LLAB-QUVVATLANMAGAN TUR JAVOBSIZ QOLMAYDI
    # ═══════════════════════════════════════════════════════════════
    class FakeUnsupported(FakeMessage):
        def __init__(self, kind):
            super().__init__()
            for k in cap._UNSUPPORTED_HINTS:
                setattr(self, k, object() if k == kind else None)

    for kind in cap._UNSUPPORTED_HINTS:
        m = FakeUnsupported(kind)
        await cap.handle_unsupported(m)
        assert m.sent, f"KRITIK: '{kind}' uchun bot JIM qoldi"
        body, kb = m.sent[0]
        assert cap._UNSUPPORTED_HINTS[kind].split()[0] in body, (kind, body[:80])
        assert "cap:menu" in {b.callback_data for b in _all_buttons(kb)}, kind
    print(f"[4] {len(cap._UNSUPPORTED_HINTS)} ta qo'llab-quvvatlanmagan tur "
          f"javobsiz qolmadi OK")

    # ── 5) Noma'lum kalit menyuga tushadi, xatoga emas ──────────────
    # Eski xabardagi tugma bosilishi mumkin — foydalanuvchi aybdor emas.
    m = FakeMessage()
    await cap.handle_capabilities_callback(FakeQuery("cap:allaqachonyoq", m))
    assert m.edited and "NIMA QILA OLAMAN" in m.edited[0][0]
    print("[5] noma'lum bo'lim menyuga qaytardi OK")

    # ═══════════════════════════════════════════════════════════════
    # 6) TUGMA STILLARI — faqat primary/success/danger
    # ═══════════════════════════════════════════════════════════════
    allowed = {BTN_PRIMARY, BTN_SUCCESS, BTN_DANGER, None}
    boards = [cap._menu_keyboard()] + [cap._section_keyboard(k) for k in cap.SECTIONS]
    for kb in boards:
        for b in _all_buttons(kb):
            style = getattr(b, "style", None)
            assert style in allowed, (
                f"KRITIK: '{style}' stili Telegram tomonidan rad etiladi va "
                f"BUTUN xabar yuborilmaydi — ekran umuman ochilmaydi")
    print("[6] barcha tugma stillari Telegram qabul qiladigan qiymatda OK")

    # ── 7) Tahrirlash yiqilsa ham ekran yetib boradi ────────────────
    m = FakeMessage(edit_ok=False)
    await cap.handle_capabilities_callback(FakeQuery("cap:chat", m))
    assert m.sent, "tahrirlash yiqilganda yangi xabar yuborilishi kerak"
    print("[7] tahrirlash yiqilsa zaxira yo'l ishladi OK")

    # ── 8) Menyuda /help bor va u ro'yxatdan o'tgan ─────────────────
    from services.menu import COMMON_COMMANDS
    assert "help" in {c.command for c in COMMON_COMMANDS}, (
        "/help menyuda bo'lmasa, ekranni faqat /start ko'rganlar topadi")
    print("[8] /help buyruqlar menyusida OK")

    print("\ncapabilities: barcha tekshiruvlar o'tdi (8/8).")


if __name__ == "__main__":
    asyncio.run(main())
