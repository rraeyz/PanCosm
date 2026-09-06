# Başlarken
Uygulama gözlem işinin tamamını tek pencerede toplar: hedef seç, geceyi planla, gözle, kalibre et, ölç, modelle ve raporla. Elinizdeki veriyle istediğiniz adımdan başlayabilirsiniz.

Her çalışma sayfasının ve sekmesinin en üstünde, sıradaki adımı söyleyen katlanmış bir **İş akışı** satırı vardır. Üzerine tıklayınca olağan iş sırası açılır (varsa IRAF görevi parantez içinde): her adım bitti (✓), atlandı (–) ya da sıradaki (▶) olarak işaretli, altında da sıradaki adım için ne yapılacağı. Bu bir rehberdir, asla kilit değildir: verinizin bulunduğu adımdan başlayın — zaten çıkarılmış bir tayfa yalnızca dalga boyları gerekir, arşivden gelen bir ışık eğrisine fotometri gerekmez — ve verinizin gerektirmediği adımları atlayın.

## İlk açılış
Uygulama ilk kez açıldığında İngilizce kısa bir karşılama penceresi üç seçim sorar:

- **Language (Dil)** — arayüz dili. Hemen uygulanır; sonradan **Ayarlar → Dil** menüsünden değiştirilebilir.
- **Computations run on (Hesaplamalar nerede)** — *Automatic (Otomatik)* ekran kartını işlemciden hızlı olduğunda kullanır (önerilen), *Graphics card (Ekran kartı)* her zaman kullanır, *Processor (CPU) only (Yalnız işlemci)* hiç kullanmaz.
- **Look (Görünüm)** — *Dark (Karanlık, gece)*: mavimsi siyah, varsayılan; ya da *Light (Aydınlık)*.

**Start (Başla)** düğmesine basın. Seçimler kaydedilir ve bir daha sorulmaz. Ardından bir dakikalık **kısa tur** gelir; atlanabilir ve **Yardım → Kısa tur** ile tekrar açılabilir.

## İlk geceniz (alıştırma verisi)
Cevabı bilinen benzetim verisiyle eksiksiz bir alıştırma: ham karelerden bir örten çiftin minimum zamanına kadar.

1. **Yardım → İlk gece için alıştırma verisi…** ve boş bir klasör seçin. Bir `raw` klasörü oluşur: birincil örtmeden geçen bir çiftin 7 bias, 7 dark (60 sn), 7 V flat ve 48 V ışık karesi; doğru cevaplar da `truth.json` dosyasında.
2. **Kalibrasyon:** `raw` klasörünü seçip **Tara**'ya basın: tablo 7 bias, 7 dark, 7 flat ve 48 ışık karesi gösterir, eksik yok. Bir çıktı klasörü seçin (ör. `cal`) ve **Kalibre et**'e basın.

![Taramadan sonra Kalibrasyon sayfası](images/tr/first-night-calibrate.png)

3. **Fotometri:** **Görüntüleri seç…** ile kalibre edilmiş `light_V_*.fits` dosyalarını seçin. **Kötü kareleri bul (bulut, odak, iz)**'ye basın: bütün kareler iyi. Görüntünün ortasındaki yıldıza (çift, x = 100, y = 80) tıklayın, sonra **Karşılaştırma yıldızı öner** (ya da diğer üç yıldıza tıklayın). Zamanlar BJD_TDB olsun diye *Hedef RA Dec* alanına `02:04:10.3 +46:41:16` yazın ve **Işık eğrisini ölç**'e basın: yaklaşık %45 derinliğinde bir örtme görünür.
4. **Örten çift yıldız: Kwee–van Woerden yöntemi** seçili kalsın (varsayılan) ve **Minimum zamanı**'na basın. Sonucu `truth.json` içindeki `t_min_bjd_tdb` ile karşılaştırın: ikisi bir iki dakika içinde uyuşur.

![Işık eğrisi ve minimum zamanıyla Fotometri sayfası](images/tr/first-night-photometry.png)

5. **Aynısı tek seferde:** **Otomasyon** sayfasında *Örten çift gecesi*'ni seçin; `raw` klasörünü, yeni bir çıktı klasörünü ve hedef konumu `100 80` olarak verip **Çalıştır**'a basın. Kalibrasyon, kare kalitesi, mukayese yıldızları, ışık eğrisi ve minimum art arda çalışır; sonuç altta görünür.

![Çalışmaya hazır Örten çift gecesi otomasyonu](images/tr/first-night-automation.png)

6. Daha ileri gitmek için: minimumu kendi referans T0 ve periyodunuzla **O-C** sekmesine yapıştırın, ışık eğrisini dışa aktarın (**CSV olarak dışa aktar…**) ya da **Yörünge ve modeller** sayfasında fit edin.

## Pencere
- **Kenar çubuğu (sol):** sayfalar bir gözlem gecesinin sırasıyla dizilidir — Başlangıç, Plan, Gözlem, Kalibrasyon, Görüntüler, Fotometri, Işık eğrileri ve O-C, Tayf, Yörüngeler ve modeller, Uzaktan algılama, Otomasyon, Proje ve bu Kılavuz.
- **Görevler paneli (alt):** her uzun iş (kalibrasyon, fotometri, fit, tayf…) arka planda kendi sürecinde çalışır. Panel ilerlemesini ve durumunu gösterir (sırada, çalışıyor, bitti, başarısız, iptal). Görevler çalışırken çalışmaya devam edebilirsiniz; çöken bir görev pencereyi düşürmez.
- **Durum çubuğu:** görüntü açıkken farenin altındaki pikselin değeri ve gök koordinatları; görevler çalışırken ilerleme çubuğu.
- **Menüler:** Dosya (projeler, FITS), Görünüm (yakınlaştırma ve görüntü germe), Görüntü (plaka çözümü, işlemler), Eklentiler, Ayarlar ve Yardım.
- **Geri al ve ileri al:** Düzen → Geri al (Ctrl+Z) gösterilen sayfadaki son değişikliği geri alır — işaretlenen ya da kaldırılan bir yıldız, silinen noktalar, bir detrend, atılan aykırı noktalar, bir görüntü işlemi, bir başlık değişikliği, tanımlanan ya da dışlanan bir ark çizgisi — Düzen → İleri al (Ctrl+Y ya da Ctrl+Shift+Z) adım adım yeniden yapar. Menü, adımın adını gösterir. Bir metin alanında Ctrl+Z o alandaki yazmayı geri alır.

## Başlangıç sayfası
Başlangıç sayfası işin alanlarından oluşan bir menüdür:

- **Kaldığınız yerden devam edin** (devam edilecek bir şey varsa): son projeler ve her alanın son dosyaları; yeniden açmak için birine çift tıklayın.
- **Yeni proje / Proje aç…** kareleri, ayarları ve sonuçları bir arada tutar. **FITS görüntüsü aç** bir görüntüye ve başlığına bakmak için.
- **Ne yapmak istediğinizi seçin:** her alan için bir blok — Planlama, Gözlem, Kalibrasyon, Görüntüler, Fotometri, Işık eğrileri, periyot ve O−C, Tayf, Modeller, Uzaktan algılama, Otomasyon — her birinde ne yaptığını söyleyen bir satır. Tıklayınca alan açılır. Alanlar kendi menüleri, araç çubuğu ve panelleri olan ayrı pencerelere taşınıyor; kendi penceresinde olan bir alan öne getirilir, asla iki kez açılmaz.
- **Pencere** menüsü: ana pencere ve açık her alan penceresi. **Yardım → Sorun bildir…** geliştiriciye göndermek için tek bir zip hazırlar (hata kaydı, sürüm, sistem, ayarlar, son adımlar; veri dosyası ve klasör adı yok). **Görünüm → Yazı boyutu** her penceredeki yazıyı büyütür ya da küçültür (Ctrl+Shift++ / − / 0).

## Projeler
Proje, uzantısı `.astroproj` olan tek bir dosyadır. Eklediğiniz her dosyayı ve çalıştırdığınız her adımı kaydeder: hangi adım, ayarları, ne zaman başladığı, başarılı olup olmadığı ve sonuçları, kullanılan kütüphanelerin sürümleriyle birlikte. Böylece iş tekrar üretilebilir: aylar sonra bir sayının nasıl elde edildiğini tam olarak görebilirsiniz.

- **Dosya → Yeni proje…** dosyayı oluşturur; **Dosya → Proje aç…** önceki işe devam eder.
- Dosya yolları proje dosyasına göre göreli saklanır; proje klasörünü verisiyle birlikte başka bir bilgisayara taşıyabilirsiniz.
- **Proje** sayfası dosyaları (türleriyle) ve çalıştırmaların geçmişini ayarlarıyla listeler.
- Geçmişte bir satır seçince o çalıştırmanın her şeyi görünür: girdileri, ayarları, sonuçları (ya da hatası) ve kütüphane sürümleri. **Aynı girdi ve ayarlarla yeniden çalıştır** onu birebir tekrarlar; tekrar yeni bir çalıştırma olarak kaydedilir.
- Proje açmadan da çalışabilirsiniz; o zaman hiçbir şey kaydedilmez.

## Ayarlar
- **Temel ya da Uzman** (Başlangıç sayfasında ya da **Ayarlar → Uzman modu**): Temel modda az değiştirilen seçenekler (diğer kalibrasyon ve yığma seçenekleri, fotometrinin seeing / PSF / sintilasyon seçenekleri, diğer araçlar) katlıdır — tek tıkla açılır, hiçbir şey kaldırılmaz — ve Tayf sayfası sekmelerinin sırasını gösterir; Uzman modda her bölüm açıktır.
- **Ayarlar → Dil:** İngilizce, Türkçe, Almanca ya da İspanyolca. Bütün metinlerin değişmesi için yeniden başlatmak gerekebilir.
- **Ayarlar → Görünüm:** Karanlık (gece) ya da Aydınlık. Ekrandaki grafikler yeni renklere geçer. Her grafiğin araç çubuğundaki **Yayın şekli…** görünüm ne olursa olsun onu beyaz zemine siyah olarak kaydeder (PDF, SVG, EPS ya da 300 dpi PNG); her tabloya sağ tıklayıp CSV ya da LaTeX olarak dışa aktarabilirsiniz.
- **Ayarlar → İşlem birimi:** Otomatik, Yalnız işlemci ya da GPU. Durum çubuğu hangi birimin kullanıldığını gösterir. GPU'yu denetlemek için uygulamayı `--benchmark` ile çalıştırın: bir GPU bulunup bulunmadığını söyler, her GPU işini (yığınlama, k-means sınıfları, ters evrişim, BLS ve PDM dönem aramaları) iki birimde de çalıştırır, sonuçların aynı olup olmadığını ve her birinin ne kadar sürdüğünü yazar (ayarlar klasörüne `gpu-check.txt` olarak da kaydedilir).
- Ayarlar kullanıcı ayar klasörünüzde küçük bir JSON dosyasında durur; eklentiler ve kendi otomasyonlarınız da onun yanındadır.

## Ekran kartı (GPU)
Ağır dizi hesapları (ör. sigma kırpmalı yığma) Vulkan, Metal ya da DirectX 12 üzerinden ekran kartında çalışabilir. Her GPU hesabının aynı sonucu veren bir işlemci (CPU) karşılığı vardır; *Otomatik* kartı yalnızca gerçekten daha hızlıysa kullanır. Kullanılabilir bir sürücü bulunmazsa işlemci kullanılır, başka hiçbir şey değişmez.
