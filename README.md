# MediaPipe El Takip ve Çizim Projesi

Bu proje, MediaPipe kütüphanesini kullanarak el hareketlerini takip eden ve havada çizim yapmanızı sağlayan bir uygulamadır.

## Özellikler

- Gerçek zamanlı el takibi
- Parmak hareketleriyle havada çizim yapma
- Farklı el jestleriyle çizim kontrolü
- Renk değiştirme ve silgi özellikleri
- Çizimi kaydetme imkanı

## Kurulum

1. Python sanal ortam (3.10.11):
```bash
py -3.10.11 -m venv myVenv

python -m pip install --upgrade pip

```

2. Gerekli paketleri yükleyin:
```bash
pip install -r requirements.txt
```

3. Uygulamayı çalıştırın:
```bash
python deneme.py(gelişim version)
```
veya
```bash
python deneme2.py
```

## Kullanım

### deneme.py - Gelişmiş Çizim Sistemi

**El Jestleri:**
- 1 parmak (işaret parmağı): Çizim yapma
- 2 parmak (V işareti): Silgi modu
- 3 parmak: Renk değiştirme
- 5 parmak (açık el): Tüm çizimi temizleme
- Yumruk: Çizimi durdurma

**Klavye Kontrolleri:**
- `u`: Kullanıcı arayüzünü açma/kapatma
- `s`: Çizimi kaydetme
- `ESC`: Uygulamadan çıkış

### deneme2.py - Basit Çizim Uygulaması

**El Jestleri:**
- İşaret parmağı: Çizim yapma
- Yumruk: Çizimi bitirme
- V işareti: Çizimi temizleme
- Açık el: Boşluk ekleme
- Başparmak: Yeni satır
- Serçe parmak: Geri alma

**Klavye Kontrolleri:**
- `s`: Çizim ve metni kaydetme
- `q`: Uygulamadan çıkış

## Gereksinimler

- Webcam
- Windows/Linux/macOS

## Dosya Yapısı

```
Mediapipe_isi2/
├── Mediapipe_isi/
│   ├── deneme.py          # Gelişmiş çizim sistemi
│   ├── deneme2.py         # Basit çizim uygulaması
├── requirements.txt       # Gerekli paketler
└── README.md             # Bu dosya
```

## Notlar
- İyi aydınlatma koşullarında daha iyi sonuç alırsınız
- El hareketlerinizi kameraya net bir şekilde gösterin
