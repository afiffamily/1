# -*- coding: utf-8 -*-
"""build_rich_markdown() havolalarni buzmasligini tekshiradi.

Nimani qo'riqlaydi:
  URL ichida sana bo'lishi odatiy hol — `.../uz/2026-08-20/dollar-oshdi/...`.
  Himoyasiz qolsa, sana naqshi uni topib `<tg-time>` tegiga o'raydi. Natijada
  havola ochilmaydigan bo'ladi VA `markdown` maydoniga HTML-only teg tushib,
  Telegram parseri to'xtaydi — butun xabar xom ko'rinadi, hatto oddiy
  `*yulduzcha*`lar ham. Ya'ni bitta havola butun javobning bezagini o'chiradi.

  Shu bilan birga MATNDAGI haqiqiy sana hamon `<tg-time>` ga o'ralishi kerak —
  aks holda tuzatish foydali xususiyatni o'ldirgan bo'lardi.

Ishga tushirish:
    PYTHONIOENCODING=utf-8 python tests/test_rich_markdown.py
"""
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from services.ai import build_rich_markdown


def test_url_sanasi_tegilmaydi():
    url = ("https://uz.kursiv.media/uz/2026-08-20/"
           "dollar-oshdi-21-avgust-uchun-valyutalar-kursi-elon-qilindi/")
    out = build_rich_markdown(f"- [Kursiv Uzbekistan]({url})")
    assert url in out, f"URL o'zgartirildi:\n{out}"
    assert "<tg-time" not in out, f"havolaga vaqt tegi qo'yildi:\n{out}"
    print("[1] markdown havola ichidagi sana tegilmadi OK")


def test_yalangoch_url_ham_himoyalangan():
    url = "https://cbu.uz/uz/kurs/2026-08-21/"
    out = build_rich_markdown(f"Manba: {url}")
    assert url in out and "<tg-time" not in out, out
    print("[2] yalang'och URL ichidagi sana tegilmadi OK")


def test_matndagi_sana_hamon_ishlaydi():
    out = build_rich_markdown("Bugun, 2026-08-21 kuni kurs e'lon qilindi.")
    assert "<tg-time" in out, f"matndagi sana tegga o'ralmadi:\n{out}"
    print("[3] matndagi haqiqiy sana hamon <tg-time> ga o'raladi OK")


def test_ikkalasi_bir_xabarda():
    """Eng muhim holat — xuddi shu xato jonli javobda shunday ko'rindi."""
    url = "https://uz.kursiv.media/uz/2026-08-20/dollar-oshdi/"
    out = build_rich_markdown(
        f"Bugun, 2026-08-21 kuni kurs o'zgardi.\n\nManba: [Kursiv]({url})")
    assert url in out, f"URL buzildi:\n{out}"
    matn, havola = out.split("Manba:")
    assert "<tg-time" in matn, "matndagi sana tegilmay qoldi"
    assert "<tg-time" not in havola, f"havolaga teg qo'yildi:\n{havola}"
    print("[4] bir xabarda: matn sanasi o'raldi, URL sanasi tegilmadi OK")


def test_url_dagi_dollar_belgisi():
    """URL ichidagi `$` matematika deb qabul qilinmasligi kerak."""
    url = "https://example.com/narx?a=$100$&b=2"
    out = build_rich_markdown(f"Havola: {url}")
    assert url in out, f"URL buzildi:\n{out}"
    assert "<tg-math" not in out, out
    print("[5] URL ichidagi $ matematika deb olinmadi OK")


def test_kod_bloki_himoyada_qoldi():
    kod = "```python\nsana = '2026-08-21'\n```"
    out = build_rich_markdown(kod)
    assert out == kod, f"kod bloki o'zgardi:\n{out}"
    print("[6] kod bloki avvalgidek himoyalangan OK")


if __name__ == "__main__":
    test_url_sanasi_tegilmaydi()
    test_yalangoch_url_ham_himoyalangan()
    test_matndagi_sana_hamon_ishlaydi()
    test_ikkalasi_bir_xabarda()
    test_url_dagi_dollar_belgisi()
    test_kod_bloki_himoyada_qoldi()
    print("\nrich_markdown: barcha tekshiruvlar o'tdi (6/6).")
