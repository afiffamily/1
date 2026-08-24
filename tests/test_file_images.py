"""Hujjat (PPTX/PDF) ichiga internetdan rasm qo'yish uchun tekshiruvlar.

Ishga tushirish:
    PYTHONIOENCODING=utf-8 python tests/test_file_images.py

Tarmoqqa CHIQMAYDI — rasm qidiruvi soxta funksiya bilan almashtiriladi.
Faqat bitta haqiqiy sandbox ishga tushirish bor (7-tekshiruv).
"""
import asyncio
import io
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from PIL import Image

import services.ai as ai
from services.sandbox import run_in_sandbox, _safe_extra_name

failures = []


def check(n, label, cond):
    print(f"[{n}] {label} {'OK' if cond else 'XATO'}")
    if not cond:
        failures.append(label)


def make_image(fmt="WEBP", size=(80, 60), mode="RGB") -> bytes:
    buf = io.BytesIO()
    Image.new(mode, size, (200, 30, 30)).save(buf, format=fmt)
    return buf.getvalue()


# ─────────────────────────────────────────────────────────────
# 1-3. RASMNI JPEG'GA O'GIRISH
# ─────────────────────────────────────────────────────────────
webp = make_image("WEBP")
jpeg = ai._to_jpeg(webp)
check(1, "WEBP -> JPEG o'giriladi (python-pptx WEBP'ni qabul qilmaydi)",
      jpeg is not None and jpeg[:2] == b"\xff\xd8")

# RGBA (shaffof PNG) — JPEG shaffoflikni bilmaydi, RGB'ga o'tishi shart.
rgba = make_image("PNG", mode="RGBA")
check(2, "RGBA -> RGB (JPEG shaffoflikni qo'llab-quvvatlamaydi)",
      ai._to_jpeg(rgba) is not None)

big = ai._to_jpeg(make_image("PNG", size=(4000, 3000)))
with Image.open(io.BytesIO(big)) as im:
    w, h = im.size
check(3, "juda katta rasm kichraytiriladi (fayl shishmasin)",
      max(w, h) <= ai.FILE_IMAGE_MAX_SIDE)

check(4, "rasm bo'lmagan bayt None qaytaradi (HTML xato sahifasi va h.k.)",
      ai._to_jpeg(b"<html>404</html>") is None)


# ─────────────────────────────────────────────────────────────
# 5-6. NOMLASH SHARTNOMASI VA KESH
# ─────────────────────────────────────────────────────────────
calls = []


async def fake_one_image(session, query):
    calls.append(query)
    if "yo'q" in query:
        return None, ""
    return ai._to_jpeg(make_image("PNG")), "example.com"


_real_one = ai._one_image
ai._one_image = fake_one_image
try:
    files, manifest = asyncio.run(ai.download_images(
        ["Verdun jangi 1916", "bunday rasm yo'q", "Somma tanki"]))
    check(5, "nomlar TARTIB bo'yicha, topilmagani ham raqamini band qiladi",
          set(files) == {"rasm1.jpg", "rasm3.jpg"}
          and len(manifest) == 3
          and "TOPILMADI" in manifest[1]
          and manifest[2].startswith("rasm3.jpg"))

    # Kesh: o'sha so'rovlar qayta yuklanmasin (model kodni tuzatib
    # qayta chaqirganda aynan o'sha rasmlar qolishi kerak).
    cache = {}
    calls.clear()
    f1, _ = asyncio.run(ai.download_images(["Verdun jangi 1916"], cache=cache))
    first_round = len(calls)
    f2, _ = asyncio.run(ai.download_images(["Verdun jangi 1916"], cache=cache))
    check(6, "kesh: ikkinchi raundda qayta yuklanmaydi va rasm o'zgarmaydi",
          first_round == 1 and len(calls) == 1
          and f1["rasm1.jpg"] == f2["rasm1.jpg"])

    check(7, "chegaradan ortiq so'rov kesiladi",
          len(asyncio.run(ai.download_images(
              [f"q{i}" for i in range(20)]))[1]) == ai.FILE_IMAGE_MAX_QUERIES)

    check(8, "bo'sh ro'yxat — hech narsa qilinmaydi",
          asyncio.run(ai.download_images([])) == ({}, [])
          and asyncio.run(ai.download_images(None)) == ({}, []))
finally:
    ai._one_image = _real_one


# ─────────────────────────────────────────────────────────────
# 9-10. SANDBOX QO'SHIMCHA FAYLLARNI QABUL QILADIMI
# ─────────────────────────────────────────────────────────────
check(9, "fayl nomi tozalanadi (ish papkasidan tashqariga yozib bo'lmaydi)",
      _safe_extra_name("../../etc/passwd") == "passwd"
      and _safe_extra_name("a/b/rasm1.jpg") == "rasm1.jpg"
      and _safe_extra_name("") == "file.bin")

code = (
    "import os\n"
    "assert os.path.exists('rasm1.jpg'), 'rasm1.jpg yo\\'q'\n"
    "size = os.path.getsize('rasm1.jpg')\n"
    "open('output/natija.txt', 'w', encoding='utf-8').write(str(size))\n"
    "print('hajm', size)\n"
)
res = asyncio.run(run_in_sandbox(code, extra_files={"rasm1.jpg": jpeg}))
check(10, "sandbox ish papkasida rasm haqiqatan turadi",
      res.success and res.output_files
      and res.output_files[0][1].decode() == str(len(jpeg)))


# ─────────────────────────────────────────────────────────────
# 11-13. _run_file_task ULANISHI
# ─────────────────────────────────────────────────────────────
seen = {}


async def fake_download(queries, cache=None):
    seen["queries"] = queries
    seen["cache"] = cache
    return {"rasm1.jpg": b"JPEGDATA"}, ["rasm1.jpg — «test» (manba: example.com, 1 KB)"]


async def fake_sandbox(code, input_bytes=None, input_name=None, extra_files=None):
    seen["extra_files"] = extra_files
    from services.sandbox import SandboxResult
    return SandboxResult(success=True, stdout="ok",
                         output_files=[("taqdimot.pptx", b"PPTX")])


_rd, _rs = ai.download_images, ai.run_in_sandbox
ai.download_images, ai.run_in_sandbox = fake_download, fake_sandbox
try:
    shared_cache = {}
    out = asyncio.run(ai._run_file_task(
        "print(1)", quota=None, input_file_bytes=None, input_filename=None,
        output_files=[], round_num=1, image_queries=["Verdun 1916"],
        image_cache=shared_cache))
    check(11, "image_queries sandbox'gacha yetib boradi",
          seen["queries"] == ["Verdun 1916"]
          and seen["extra_files"] == {"rasm1.jpg": b"JPEGDATA"}
          and seen["cache"] is shared_cache)
    check(12, "manifest model javobiga qo'shiladi (manba ko'rsatish uchun)",
          "RASMLAR:" in out and "example.com" in out and "BAJARILDI" in out)

    seen.clear()
    asyncio.run(ai._run_file_task(
        "print(1)", quota=None, input_file_bytes=None, input_filename=None,
        output_files=[], round_num=1))
    check(13, "image_queries berilmasa rasm umuman qidirilmaydi",
          "queries" not in seen and seen.get("extra_files") is None)
finally:
    ai.download_images, ai.run_in_sandbox = _rd, _rs


print("─" * 55)
if failures:
    print(f"❌ {len(failures)} ta tekshiruv yiqildi:")
    for f in failures:
        print(f"   • {f}")
    sys.exit(1)
print("✅ Fayl ichidagi rasm tekshiruvlari — hammasi o'tdi")
