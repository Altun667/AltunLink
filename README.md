# AltunLink

Telefonla bilgisayar arasında, aynı Wi-Fi ağı üzerinden dosya köprüsü. Fotoğraf, video ve belge gönder; büyük dosyaların ilerlemesini canlı izle.

- Telefona uygulama kurmak gerekmez, tarayıcı yeterli.
- QR kodla eşleştirme. Her açılışta yeni bir kod üretilir, kodu bilmeyen bağlanamaz.
- Dosyalar internete çıkmaz, doğrudan cihazlar arasında gider.
- Gelen dosyalar `Downloads\AltunLink` klasörüne kaydedilir.

## Kurulum (kullanıcı)

[Releases](../../releases) sayfasından `AltunLink-Setup.exe` dosyasını indir ve çalıştır.
Kurulum Windows güvenlik duvarında özel ağlar için izin kuralını kendisi ekler.

## Kullanım

1. Bilgisayarda AltunLink'i aç.
2. Telefonu aynı Wi-Fi'a bağla, kamerayla QR kodu okut.
3. Telefondan "Bilgisayara dosya gönder"e bas. Bilgisayardan göndermek için "Telefona dosya gönder"i kullan.

## Kaynaktan çalıştırma

```
pip install -r requirements.txt
python altunlink.py
```

## Setup nasıl üretilir

`v1.0.0` gibi bir etiket (tag) gönderdiğinde GitHub Actions `AltunLink-Setup.exe` dosyasını kendisi üretir ve Releases'e ekler:

```
git tag v1.0.0
git push origin v1.0.0
```

## Bizi takip et

[YouTube](https://www.youtube.com/@Altun67) · [Instagram](https://www.instagram.com/altunn_67/) · [TikTok](https://www.tiktok.com/@altunn_67)
