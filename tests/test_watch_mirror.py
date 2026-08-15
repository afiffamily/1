"""Kuzatuv (watch) oynasi — foydalanuvchi savoli kuzatuvchiga yetib borishi.
Ishga tushirish: python tests/test_watch_mirror.py

NEGA KERAK: haqiqiy logdan chiqqan xato. Guest rejimda kuzatuv HAR SAFAR
"Bad Request: message to copy not found" berardi va natijada kuzatuvchi
BOT JAVOBINI ko'rib, FOYDALANUVCHI SAVOLINI ko'rmasdi — kuzatuvning butun
ma'nosi esa aynan o'sha savolda.

Sabab: guest rejimda bot chat A'ZOSI EMAS, shuning uchun copyMessage
manba xabarni topa olmaydi. To'g'ri yo'l — matnni to'g'ridan-to'g'ri
yuborish va media uchun file_id ni qayta yuborish (u update bilan keladi
va chatga kirish talab qilmaydi).
"""

import os
import sys
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
import asyncio

import handlers.helpers as helpers
from handlers.guest import _watch_text, _watch_file


class FakeBot:
    """copy_message'ni guest rejimdagidek yiqitadi."""
    def __init__(self, copy_works=False):
        self.copy_works = copy_works
        self.messages = []
        self.files = []
        self.copies = 0

    async def send_message(self, chat_id, text, **kwargs):
        self.messages.append(text)

    async def copy_message(self, chat_id, from_chat_id, message_id, **kwargs):
        self.copies += 1
        if not self.copy_works:
            raise RuntimeError("Bad Request: message to copy not found")

    async def send_photo(self, chat_id, file_id, **kwargs):
        self.files.append(("photo", file_id))

    async def send_document(self, chat_id, file_id, **kwargs):
        self.files.append(("document", file_id))

    async def send_voice(self, chat_id, file_id, **kwargs):
        self.files.append(("voice", file_id))


class FakeMsg:
    def __init__(self, text=None, caption=None, photo=None, document=None, voice=None):
        self.text = text
        self.caption = caption
        self.photo = photo
        self.document = document
        self.voice = voice


class FakeFile:
    def __init__(self, file_id):
        self.file_id = file_id


async def send(**kwargs):
    """_send_watch_copy'ni standart argumentlar bilan chaqiradi."""
    params = dict(group_id=-100, user_id=7907009046, username="shubhali",
                  direction="in", text=None, copy_chat_id=None,
                  copy_message_id=None, file_id=None, file_kind=None)
    params.update(kwargs)
    await helpers._send_watch_copy(**params)


async def main():
    real_bot = helpers.bot

    # ═══════════════════════════════════════════════════════════════
    # 1) FAQAT MATN — savol kuzatuvchiga YETIB BORADI
    #    Aynan shu buzilgan edi: guest yo'li doim copy shoxiga tushib,
    #    matn UMUMAN yuborilmasdi.
    # ═══════════════════════════════════════════════════════════════
    fake = FakeBot()
    helpers.bot = fake
    try:
        await send(text="Salom, bu mening savolim")
        assert any("mening savolim" in m for m in fake.messages), fake.messages
        assert fake.copies == 0, "matn uchun copyMessage chaqirilmasligi kerak"
        print("[1] matnli savol kuzatuvchiga yetdi OK")

        # ═══════════════════════════════════════════════════════════
        # 2) GUEST MEDIA — file_id bilan, copyMessage'siz
        # ═══════════════════════════════════════════════════════════
        for kind, fid in (("photo", "AgAC1"), ("document", "BQAC2"), ("voice", "AwAC3")):
            fake = FakeBot()
            helpers.bot = fake
            await send(file_id=fid, file_kind=kind)
            assert fake.files == [(kind, fid)], (kind, fake.files)
            assert fake.copies == 0, f"{kind}: guest'da copyMessage ishlamaydi"
        print("[2] rasm/hujjat/ovoz file_id orqali yuborildi OK")

        # ── 3) Media + matn: ikkalasi ham, sarlavha takrorlanmaydi ──
        fake = FakeBot()
        helpers.bot = fake
        await send(file_id="AgAC1", file_kind="photo", text="bu nima?")
        assert fake.files, "rasm yuborilmadi"
        assert any("bu nima?" in m for m in fake.messages), fake.messages
        headers = [m for m in fake.messages if "Kuzatuv" in m]
        assert len(headers) == 1, f"sarlavha {len(headers)} marta chiqdi, 1 bo'lishi kerak"
        print("[3] media + matn birga yetdi, sarlavha takrorlanmadi OK")

        # ── 4) Shaxsiy chatda eski copy yo'li saqlanib qoldi ────────
        fake = FakeBot(copy_works=True)
        helpers.bot = fake
        await send(copy_chat_id=555, copy_message_id=7)
        assert fake.copies == 1 and not fake.files
        print("[4] shaxsiy chatda copyMessage yo'li o'zgarmadi OK")

        # ── 5) HTML escape saqlanib qoldi ──────────────────────────
        # "agar a < b" kabi savol escape qilinmasa Telegram butun
        # kuzatuv xabarini rad etadi.
        fake = FakeBot()
        helpers.bot = fake
        await send(text="agar a < b bo'lsa")
        assert any("&lt;" in m for m in fake.messages), fake.messages
        print("[5] foydalanuvchi matni HTML-escape qilindi OK")
    finally:
        helpers.bot = real_bot

    # ═══════════════════════════════════════════════════════════════
    # 6) KUZATUVCHI FOYDALANUVCHI YOZGANINI KO'RADI, MODEL PROMPTINI EMAS
    # ═══════════════════════════════════════════════════════════════
    m = FakeMsg(text="@bot bu rasmda nima?")
    assert _watch_text(m, "") == "@bot bu rasmda nima?"
    # Rasm izohsiz kelsa modelga "Bu rasmda nimalar borligini..." ketadi,
    # lekin kuzatuvchiga foydalanuvchi yozmagan matnni ko'rsatish yolg'on.
    assert _watch_text(FakeMsg(), "") == ""
    print("[6] kuzatuvga foydalanuvchi matni ketdi, model prompti emas OK")

    # ── 7) Reply konteksti ham qo'shiladi ───────────────────────────
    q = 'Kimdir yozgan xabar:\n"""asl savol"""'
    assert "asl savol" in _watch_text(FakeMsg(text="javob ber"), q)
    print("[7] reply konteksti kuzatuvga qo'shildi OK")

    # ── 8) _watch_file to'g'ri turni tanlaydi ───────────────────────
    assert _watch_file(FakeMsg(photo=[FakeFile("p1")]), "photo") == {
        "file_id": "p1", "file_kind": "photo"}
    assert _watch_file(FakeMsg(voice=FakeFile("v1")), "voice") == {
        "file_id": "v1", "file_kind": "voice"}
    assert _watch_file(FakeMsg(text="salom"), "text") == {}
    print("[8] _watch_file turga mos file_id qaytardi OK")

    print("\nwatch mirror: barcha tekshiruvlar o'tdi (8/8).")


if __name__ == "__main__":
    asyncio.run(main())
