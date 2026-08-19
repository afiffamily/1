"""Fayl ustidagi DAVOMIY so'rovlar — botning o'z natijasi ustiga qo'yilishi.
Ishga tushirish: python tests/test_file_followup.py

NEGA KERAK: haqiqiy foydalanuvchi shikoyati. Odam .docx yubordi, bot uni
tahrirlab qaytardi; keyin "nomini ham o'zgartir" dedi va bot DASTLABKI xom
faylni olib, faqat oxirgi so'ralgan o'zgarishni qo'yib berdi — birinchi
tahrir yo'qoldi. Tashqaridan bu "bot eslab qololmayapti" bo'lib ko'rinadi.

Sabab: _remember_file() faqat foydalanuvchi YUKLAGAN faylga chaqirilardi,
botning O'ZI yaratgan natija esa yuborilib, unutilardi.
"""

import os
import sys
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
import asyncio

import handlers.messages as M
from handlers.messages import MAX_TELEGRAM_DOCUMENT_SIZE

CHAT = 424242


class FakeBot:
    def __init__(self, doc_ok=True):
        self.doc_ok = doc_ok
        self.docs = []
        self.photos = []
        self.texts = []

    async def send_document(self, chat_id, file, **kw):
        if not self.doc_ok:
            raise RuntimeError("Telegram rad etdi")
        self.docs.append(file.filename)

    async def send_photo(self, chat_id, file, **kw):
        self.photos.append(file.filename)

    async def send_message(self, chat_id, text, **kw):
        self.texts.append(text)


async def main():
    real_bot = M.bot
    M.bot = FakeBot()
    try:
        # ═══════════════════════════════════════════════════════════
        # 1) BOT YARATGAN FAYL ESLAB QOLINADI
        #    Aynan shu yo'q edi.
        # ═══════════════════════════════════════════════════════════
        M.clear_pending_file(CHAT)
        M._remember_file(CHAT, b"XOM", "56-maktab.docx")          # foydalanuvchi yubordi
        await M._send_output_files(CHAT, [("46-maktab.docx", b"TAHRIRLANGAN")])

        rec = M._get_pending_file(CHAT)
        assert rec["name"] == "46-maktab.docx", rec["name"]
        assert rec["bytes"] == b"TAHRIRLANGAN", "xom fayl qaytib qoldi"
        assert rec["produced"] is True
        print("[1] bot yaratgan fayl keyingi so'rov uchun eslab qolindi OK")

        # ═══════════════════════════════════════════════════════════
        # 2) MODELGA "DAVOM ETTIR" DEB AYTILADI
        #    Faqat faylni almashtirish yetarli emas — model uni yangi xom
        #    fayl deb bilsa, oldingi tahrirlarni baribir bekor qiladi.
        # ═══════════════════════════════════════════════════════════
        note = M.pending_file_note("46-maktab.docx", earlier=True, produced=True)
        assert "SEN oxirgi marta" in note, note
        assert "saqlanib" in note and "USTIGA" in note, note
        assert "noldan boshlamang" in note.lower(), note
        plain = M.pending_file_note("56-maktab.docx", earlier=True)
        assert "SEN oxirgi marta" not in plain, plain
        print("[2] modelga oldingi tahrirlarni saqlash aytildi OK")

        # ── 3) Yangi fayl yuklansa zanjir QAYTA boshlanadi ──────────
        M._remember_file(CHAT, b"YANGI XOM", "boshqa.docx")
        rec = M._get_pending_file(CHAT)
        assert rec["produced"] is False and rec["bytes"] == b"YANGI XOM"
        print("[3] yangi yuklangan fayl zanjirni qayta boshladi OK")

        # ── 4) Bir nechta natijadan OXIRGISI eslab qolinadi ─────────
        M.clear_pending_file(CHAT)
        await M._send_output_files(CHAT, [("a.txt", b"A"), ("b.txt", b"B")])
        assert M._get_pending_file(CHAT)["name"] == "b.txt"
        print("[4] bir nechta fayldan oxirgisi eslab qolindi OK")

        # ── 5) Rasm ham eslab qolinadi ─────────────────────────────
        M.clear_pending_file(CHAT)
        await M._send_output_files(CHAT, [("chart.png", b"PNG")])
        assert M.bot.photos == ["chart.png"]
        assert M._get_pending_file(CHAT)["name"] == "chart.png"
        print("[5] rasm natijasi ham eslab qolindi OK")

        # ═══════════════════════════════════════════════════════════
        # 6) YETIB BORMAGAN FAYL ESLAB QOLINMAYDI
        #    Aks holda foydalanuvchi KO'RMAGAN natija ustida ish
        #    davom etardi va u nimadan gap ketayotganini bilmasdi.
        # ═══════════════════════════════════════════════════════════
        M.clear_pending_file(CHAT)
        M.bot = FakeBot(doc_ok=False)
        await M._send_output_files(CHAT, [("yiqilgan.docx", b"X")])
        assert M._get_pending_file(CHAT) is None, "yuborilmagan fayl eslab qolindi"
        print("[6] yuborilmagan fayl eslab qolinmadi OK")

        # ── 7) Hajmi oshgan fayl ham eslab qolinmaydi ──────────────
        M.clear_pending_file(CHAT)
        M.bot = FakeBot()
        await M._send_output_files(CHAT, [("katta.bin", b"x" * (MAX_TELEGRAM_DOCUMENT_SIZE + 1))])
        assert M._get_pending_file(CHAT) is None
        print("[7] Telegram chegarasidan katta fayl eslab qolinmadi OK")
    finally:
        M.bot = real_bot
        M.clear_pending_file(CHAT)

    print("\nfayl davomiyligi: barcha tekshiruvlar o'tdi (7/7).")


if __name__ == "__main__":
    asyncio.run(main())
