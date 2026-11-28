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

### 9. CachyOS'ta PKGBUILD ile kurulum (bir sonraki sürümden sonra)
- **Ne:** Sürüm sayfasındaki `PKGBUILD` dosyasını boş bir klasöre koy, orada `makepkg -si` çalıştır. Program
  menüde görünüyor ve açılıyor mu? Hata verirse terminal çıktısını gönder.
- **Neden:** Arch paketi artık her sürümle geliyor (ARC-20), ama gerçek bir Arch sisteminde denenmedi; senin
  CachyOS'un tek gerçek deneme.

### 10. Windows'ta taşınabilir zip (bir sonraki sürümden sonra)
- **Ne:** `…-windows-x64-portable.zip` dosyasını bir klasöre (ya da USB belleğe) aç, içindeki `.exe`'yi çalıştır.
  Açılıyor mu, SmartScreen ne diyor?
- **Neden:** Kurulum yapılamayan bilgisayarlar (okul, gözlemevi) için ekledim (ARC-20); CI yalnızca kurulumlu
  sürümü deniyor.

### 11. NY Vir gecesi baştan sona, tıklama sayısı (bir sonraki sürümden sonra)
- **Ne:** Kendi NY Vir verinle (internet açık) Fotometri penceresini aç: görüntüleri yükle → alan tanınsın →
  hedef OBJECT'ten ya da Alan aşamasındaki "Hedefi bul" kutusuna adını yazarak bulunsun → Ölç → Minimum zamanı.
  Kaç tıklama sürdü, hangi aşamada takıldın, otomatik seçimlerin gerekçeleri anlaşılır mı?
- **Neden:** Plan bu akışı en çok 7 tıklama olarak istiyor (PHO-W). Örnek gecede 4 tıklama ölçtüm, ama Alan
  aşaması internet ve gerçek veri istediği için testte sayılamadı.

### 12. Terimler sözlüğü için tanımlar
- **Ne:** Kılavuza bir "Terimler" bölümü eklenecek (UI-7). Kısa tanım gereken terimlerin listesini hazırlayıp sana
  göndereceğim; her biri için bir cümlelik Türkçe tanımı onaylaman ya da düzeltmen yeterli.
- **Neden:** Tanımları uydurmamam gerekiyor; senin onayın olmadan yazılmayacak.

### 13. İki ekranla deneme (bir sonraki sürümden sonra)
- **Ne:** İki monitörlü bir bilgisayarda bir alan penceresini ve bir sonuç sekmesini ikinci ekrana taşı, programı
  kapatıp aç: aynı yerlerde açılıyor mu? Sonra ikinci ekranı çıkarıp aç: pencereler görünen ekrana geliyor mu?
- **Neden:** Bu davranışı ekledim (UI-14), ama burada tek sanal ekran var; gerçek iki ekranla denenmedi.

### 14. Windows'ta saat dilimi için `tzdata` paketi
- **Ne:** Profile saat dilimi (ör. Europe/Istanbul) eklendi; Planlama yerel saatleri ona göre gösteriyor. Windows'ta
  Python'un saat dilimi veritabanı yok, `tzdata` paketi gerekiyor. Bağımlılık eklemek senin onayını istiyor:
  ekleyeyim mi?
- **Neden:** Paket yokken Windows'ta saat dilimi yok sayılıyor (program çökmüyor, eski davranış: UTC farkı elle ya
  da boylamdan). Linux ve macOS'ta sorun yok.

### 15. Türkçede iki türlü çevrilmiş terimler
- **Ne:** Sözlüğe (glossary.toml) yalnız her yerde aynı çevrilen terimler girdi (225 terim). Aşağıdakiler programda
  iki ya da daha çok biçimde geçiyor; her biri için hangisi kalsın, yazman yeterli, gerisini ben düzeltirim:
  gök halkası / gökyüzü halkası (6 metinde geri kaymış) · gök / gökyüzü parlaklığı · plaka / plak çözümü (yazım
  hatası) · minör gezegen / küçük gezegen · filtre / süzgeç · medyan / ortanca · dizi / sekans · epok / çevrim /
  sıfır anı · binning / binleme / birleştirme · kadans / kare aralığı · trend / eğilim (detrend) · tayfçeker /
  spektrograf · çözünürlük / ayırma gücü · ilinti / korelasyon · döndürücü / rotator · genişleme fonksiyonu
  (bazı yerlerde İngilizce kalmış) · kayma / ofset · kuadratik / ikinci derece · çevrim / döngü · birincil /
  baş yıldız · paralaks / ıraklık açısı · periastron / enberi · alet / cihaz · doymuş / doygun · evrelenmiş /
  katlanmış ışık eğrisi.
- **Neden:** Hangisinin doğru olduğuna kendim karar verip uydurmak istemedim; seçimin sözlüğe girecek ve test bundan
  sonra kaymayı yakalayacak.

## Bitti

(henüz yok)
