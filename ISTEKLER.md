# Senden istediklerim

Müsait olduğunda yap, sonucu gönder. Her maddede ne için istediğim ve sonucu nereye kullanacağım yazıyor.
Yapılanları "Bitti" altına taşıyacağım.

## Bekleyenler

### 1. GPU raporu (RTX 4050)
- **Ne:** Programda Yardım → "GPU'yu denetle" çalıştır, oluşan `gpu-report.json` dosyasını gönder.
- **Neden:** GPU hızlandırmasının gerçek kartta doğru ve hızlı çalıştığını görmem gerek (plans/architecture.md ARC-10).
  Bulut makinelerinde GPU yok; senin kartın tek gerçek ölçüm.

### 2. Sözlüğün Türkçe sütunu
- **Ne:** `src/astrowb/resources/i18n/glossary.toml` dosyasındaki Türkçe karşılıkları bir kez oku; yanlış ya da
  alışılmamış bulduğunu yaz (örneğin "plaka çözümü" mü "astrometrik çözüm" mü).
- **Neden:** Programdaki bütün Türkçe metinler bu sözlüğe göre denetleniyor (ARC-18). Bir terim yanlışsa her yerde yanlış olur.

### 3. Yeni Fotometri penceresini dene (0.3.8)
- **Ne:** NY Vir verinle Fotometri penceresinde baştan sona bir ölçüm yap. Ne yapacağının belirsiz kaldığı
  bir aşama olursa ekran görüntüsünü gönder ve kısaca neyi beklediğini yaz.
- **Neden:** Sol paneli aşamalara (Görüntüler … Rapor) böldüm (UI-16.1). Diğer pencereleri de bu düzene
  geçirmeden önce düzenin sana uygun olduğundan emin olmak istiyorum.

### 4. Kalibrasyon penceresi: iki sütun mu, aşamalar mı?
- **Ne:** Kalibrasyon şu an iki sütunlu. Küçük ekranda hiçbir şey aşağıda kalmasın diye böyle istemiştin.
  Fotometri'deki gibi aşamalara bölersem iki sütun aynı anda görünmez, sırayla görünür. Hangisi olsun?
- **Neden:** UI-16.2'ye bu karara göre başlayacağım. Senin eski tercihini kendi başıma bozmak istemedim.

### 5. Spektroskopi'deki "Hangi sırayla?" paneli
- **Ne:** Bu paneli sen istediğin için pencerede bıraktım. Diğer uzun açıklamalar gibi tek satıra indirip
  "Ayrıntı…" ile kılavuza bağlayayım mı, yoksa olduğu gibi mi kalsın?
- **Neden:** Panellerde 140 karakterden uzun metin bırakmama kuralı var (UI-7); bu tek istisna.

### 6. Araç çubuğu yazıları varsayılan olarak açık mı olsun?
- **Ne:** Şu an araç çubuklarında yalnızca ikonlar görünüyor; Görünüm → "Araç çubuğu yazıları" ile adlar açılıyor.
  Plan, adların varsayılan olarak açık olmasını öneriyor. Ne istersin?
- **Neden:** UI-2 madde 4. Ayar dosyasından senin bilinçli seçiminle eski varsayılanı ayırt edemediğim için kendim değiştirmedim.

### 7. Kırmızı gece teması
- **Ne:** Teleskop başında göz uyumunu bozmayan, siyah üzerine kırmızı bir tema hazır ama menüde yok.
  Ayarlar'da seçenek olarak açayım mı?
- **Neden:** interface.md "To ask the owner" listesinde bekliyor.

### 8. Kendi makinelerinde ekran görüntüleri
- **Ne:** Windows ve CachyOS makinelerinde, gerçek ölçekleme (ör. %125) ile başlangıç penceresinin ve Fotometri
  penceresinin birer ekran görüntüsü.
- **Neden:** Testler sanal ekranda 1366 × 768'de çalışıyor. Gerçek ölçeklemede yazı kesilmesi ya da taşma olup
  olmadığını ancak böyle görebilirim (UI-5, UI-16.1).

## Bitti

(henüz yok)
