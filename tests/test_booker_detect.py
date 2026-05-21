"""Başarı/hata metin ayrımı — yanlış pozitif önleme."""

import re


def test_error_flash_not_counted_as_success():
    error = "Üzgünüz katılım kaydedilirken bir sorun oluştu"
    strict_ok = re.compile(r"başarıyla|katılımınız.*oluşturuldu", re.I)
    assert not strict_ok.search(error)


def test_error_message_matches_not_open():
    msg = "Katılımlar oluşturmak için çok erken, kayıtlar 4 günler öncesi açılıyor"
    error_pat = re.compile(
        r"sorun oluştu|çok erken|kayıtlar.*açılıyor|4\s*gün.*önce",
        re.I,
    )
    assert error_pat.search(msg)
