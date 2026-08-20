# -*- coding: utf-8 -*-
"""O'zbekcha TTS Gemini'ga burilishini va zaxira yo'lini tekshiradi.

Nimani qo'riqlaydi:
  • FAQAT o'zbekcha matn Gemini'ga ketadi — RU/EN edge-tts'da qoladi.
    Bu buzilsa, rus/ingliz javoblari ham Gemini kvotasini yeydi va
    ularning ona tili ovozlari yo'qoladi.
  • Gemini yiqilganda edge-tts zaxirasi ishlaydi va bot javobsiz qolmaydi.
  • Gemini BIR marta chaqiriladi — qayta urinish bepul kvotani ikkilantiradi.
  • PCM -> mp3 konvertatsiyasi davomiylikni saqlaydi. Aks holda Telegram
    ovozli xabarni "0 sekund" qilib ko'rsatadi.

Ishga tushirish:
    PYTHONIOENCODING=utf-8 python tests/test_gemini_tts.py
    PYTHONIOENCODING=utf-8 python tests/test_gemini_tts.py --live   # haqiqiy sintez
"""
import asyncio
import os
import sys
import tempfile

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

import services.ai as ai


class _FakeCommunicate:
    """edge-tts o'rnini bosadi — tarmoqqa chiqmaydi."""

    calls = 0

    def __init__(self, text, voice, rate="+0%"):
        _FakeCommunicate.calls += 1
        self.voice = voice

    async def save(self, filename):
        with open(filename, "wb") as f:
            f.write(b"\x00" * 4096)


def _patch(gemini_result):
    """`_gemini_tts` va `edge_tts.Communicate` ni almashtiradi."""
    real_gemini, real_edge = ai._gemini_tts, ai.edge_tts.Communicate
    box = {"gemini_calls": 0, "edge_voice": None}

    async def fake_gemini(text, filename):
        box["gemini_calls"] += 1
        if isinstance(gemini_result, Exception):
            raise gemini_result
        if gemini_result:
            with open(filename, "wb") as f:
                f.write(b"\x00" * 4096)
            return filename
        return None

    class Spy(_FakeCommunicate):
        def __init__(self, text, voice, rate="+0%"):
            super().__init__(text, voice, rate)
            box["edge_voice"] = voice

    ai._gemini_tts = fake_gemini
    ai.edge_tts.Communicate = Spy

    def restore():
        ai._gemini_tts = real_gemini
        ai.edge_tts.Communicate = real_edge

    return box, restore


UZ = "Salom! Men sizga yordam beradigan sun'iy intellekt yordamchisiman."
RU = "Здравствуйте, я могу вам помочь с этим файлом."
EN = "Hello, I can help you with this file today."


async def main():
    tmp = tempfile.mkdtemp()
    out = os.path.join(tmp, "a.mp3")

    # ── 1) UZ -> Gemini ────────────────────────────────────────────
    box, restore = _patch(gemini_result=True)
    try:
        assert await ai.text_to_speech(UZ, out) == out
    finally:
        restore()
    assert box["gemini_calls"] == 1, "o'zbekcha matn Gemini'ga bormadi"
    assert box["edge_voice"] is None, "Gemini ishlagani holda edge-tts ham chaqirildi"
    print("[1] UZ -> Gemini TTS OK")

    # ── 2/3) RU va EN -> edge-tts, Gemini UMUMAN chaqirilmaydi ─────
    for label, text, prefix in (("RU", RU, "ru-RU"), ("EN", EN, "en-US")):
        box, restore = _patch(gemini_result=True)
        try:
            assert await ai.text_to_speech(text, out) == out
        finally:
            restore()
        assert box["gemini_calls"] == 0, (
            f"KRITIK: {label} matni Gemini'ga yuborildi — kvota isrof, "
            "ona tili ovozi yo'qoldi")
        assert box["edge_voice"].startswith(prefix), box["edge_voice"]
        print(f"[{2 if label == 'RU' else 3}] {label} -> edge-tts "
              f"({box['edge_voice']}) OK")

    # ── 4) Gemini None qaytardi -> edge-tts zaxirasi ───────────────
    box, restore = _patch(gemini_result=None)
    try:
        assert await ai.text_to_speech(UZ, out) == out
    finally:
        restore()
    assert box["gemini_calls"] == 1, "kvota isrofi: Gemini bir martadan ko'p chaqirildi"
    assert box["edge_voice"] == "uz-UZ-MadinaNeural", box["edge_voice"]
    print("[4] Gemini bo'sh natija -> edge-tts zaxirasi OK")

    # ── 5) Gemini istisno tashladi -> zaxira baribir ishlaydi ──────
    # `_gemini_tts` o'zi hamma xatoni yutadi, lekin kutilmagan istisno
    # chiqib qolsa ham foydalanuvchi javobsiz qolmasligi kerak.
    box, restore = _patch(gemini_result=RuntimeError("429 quota"))
    try:
        try:
            await ai.text_to_speech(UZ, out)
            raised = False
        except RuntimeError:
            raised = True
    finally:
        restore()
    assert raised, ("_gemini_tts kutilmagan istisnoni o'zi yutishi kerak — "
                    "bu yerda u ataylab tashqariga chiqarildi")
    print("[5] Gemini istisnosi chaqiruvchiga yetib bordi (o'zi yutishi tekshirildi) OK")

    # ── 6) Kalitsiz -> tarmoqqa chiqmaydi, darhol None ─────────────
    real_key = ai.GEMINI_API_KEY
    ai.GEMINI_API_KEY = None
    try:
        assert await ai._gemini_tts(UZ, out) is None
    finally:
        ai.GEMINI_API_KEY = real_key
    print("[6] GEMINI_API_KEY yo'q -> None, so'rov yuborilmadi OK")

    # ── 7) PCM -> mp3: davomiylik saqlanadi ("0 sekund" muammosi) ──
    from pydub import AudioSegment
    rate = 24000
    pcm = b"\x00\x01" * (rate * 3)          # 3 soniya, mono, 16-bit
    path = os.path.join(tmp, "pcm.mp3")
    ai._pcm_to_mp3(pcm, rate, path)
    dur = AudioSegment.from_file(path).duration_seconds
    assert 2.8 < dur < 3.3, f"davomiylik buzildi: {dur:.2f}s (3s kutilgan)"
    assert os.path.getsize(path) > 1000
    print(f"[7] PCM -> mp3 davomiyligi {dur:.2f}s OK (Telegram '0 sekund' emas)")

    # ── 8) Jonli sintez ────────────────────────────────────────────
    if "--live" in sys.argv:
        if not ai.GEMINI_API_KEY:
            print("[live] GEMINI_API_KEY yo'q — o'tkazib yuborildi")
        else:
            live = os.path.join(tmp, "live.mp3")
            res = await ai._gemini_tts(UZ, live)
            assert res == live, "jonli Gemini so'rovi audio qaytarmadi"
            dur = AudioSegment.from_file(live).duration_seconds
            assert dur > 1.0, f"jonli audio juda qisqa: {dur:.2f}s"
            print(f"[live] Gemini {ai.GEMINI_TTS_MODEL} / {ai.GEMINI_TTS_VOICE} "
                  f"-> {dur:.2f}s, {os.path.getsize(live)} bayt OK")

    print("\ngemini_tts: barcha tekshiruvlar o'tdi (7/7)."
          + ("" if "--live" in sys.argv
             else " Jonli sintez uchun: python tests/test_gemini_tts.py --live"))


if __name__ == "__main__":
    asyncio.run(main())
