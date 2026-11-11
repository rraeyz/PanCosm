# Sorun giderme
Sık karşılaşılan sorunlar ve yapılacaklar.

## Bir görev başarısız oldu {#troubleshooting-task-failed}
Görevler paneli *başarısız* gösterir ve bir pencere hatayı verir. Tipik nedenler: okunamayan bir dosya, eksik bir girdi (ileti adını söyler), çok az yıldız ya da kare. Pencere kullanılabilir kalır; girdiyi düzeltip adımı yeniden çalıştırın. Projenin geçmişi başarısız çalıştırmayı ayarlarıyla saklar.

Hata penceresi hatanın kendisini gösterir; **Ayrıntıları Göster…** tam raporu içerir. Kurulumu ve uygulamanın kullandığı her web servisini (SIMBAD, VizieR, MAST, ZTF, AAVSO, SkyBoT, …) denetlemek için **Yardım → Kurulumu ve internet servislerini denetle**'yi seçin (ya da uygulamayı terminalden `--check-online` ile çalıştırın): her satır OK ya da FAIL ve nedenini söyler. Tek bir servisteki FAIL genelde o servisten ya da ağınızdan kaynaklanır; ilk satırlardaki bir FAIL kurulumun bir parçasının eksik olduğu anlamına gelir — lütfen bildirin.

## Kalibrasyon karelerin eksik olduğunu söylüyor {#troubleshooting-calibration-frames-missing}
"no flat for filter …", "no dark for … s", "no bias" — o light'lar yine o düzeltme olmadan kalibre edilir. Eksik kareleri alın (aynı filtre, binning, poz ve sıcaklık) ya da sonucu kabul edin. Başka pozdaki dark'lar yalnızca bias kareleriyle kullanılabilir.

## Yıldızlar bulunmuyor ya da ışık eğrisi sıçrıyor {#troubleshooting-stars-not-found-light}
- Görüntülerin kalibre ve tek filtreden olduğundan emin olun.
- Odak dışı ya da iz bırakan yıldızlar için açıklığı büyütün; gök halkasını komşulardan uzaklaştırın.
- Alan çok kayıyorsa hedefin her karede içeride olduğunu kontrol edin; olmadığı kareler atlanır.
- Başka karşılaştırma yıldızları seçin: biri değişken ya da doymuş olabilir.

## Zamanlar yanlış görünüyor {#troubleshooting-times-look-wrong}
Başlıktaki `DATE-OBS`'u (pozun UTC başlangıcı olmalı) ve `EXPTIME`'ı kontrol edin. BJD için hedefin koordinatları ve gözlem yeri bilinmelidir (başlıkta ya da penceredeki alanlarda).

## Plaka çözümü bir şey yapmıyor {#troubleshooting-plate-solving-nothing}
ASTAP'ı bir yıldız veritabanıyla (ya da astrometry.net'i indeks dosyalarıyla) kurun ve yeniden deneyin. Başlıktaki yaklaşık koordinatlar işi çok hızlandırır. Çok küçük alanlar daha derin bir veritabanı ister.

## Gözlemevi GÜVENLİ DEĞİL diyor {#troubleshooting-observatory-not-safe}
Nedenler listelenir: Güneş doğmuş, hedef çok alçak, nem, rüzgâr, yağmur, yanıt vermeyen bir cihaz… Nedeni giderin, sonra **Devam et**'e basın. Bir şey hâlâ güvensizken Devam et reddedilir — bu bilerek böyledir.

## Gözlemeviyle bağlantı yok {#troubleshooting-no-connection-observatory}
Gözlemevi sürecinin çalıştığını (**Gözlemevini bu bilgisayarda başlat…** ile yeniden başlatın), adresi ve erişim anahtarını kontrol edin. Uzak bir bilgisayarda güvenlik duvarı portu engelliyor olabilir.

## Ekran kartı kullanılmıyor {#troubleshooting-graphics-card-not-used}
**Ayarlar → İşlem birimi** kipi gösterir; durum çubuğu birimin adını verir. *Otomatik* kipte kart yalnızca daha hızlıysa kullanılır. Kart bulunmuyorsa ekran kartı sürücüsünü güncelleyin; her şey işlemcide de çalışır.

## Ayarlarım ve dosyalarım nerede? {#troubleshooting-where-settings-files}
Ayarlar, eklentiler ve otomasyonlar kullanıcı ayar klasöründedir (Linux'ta `~/.config/…`, Windows'ta `%LOCALAPPDATA%\…`, macOS'ta `~/Library/Application Support/…`). Projeler ve sonuçlar sizin kaydettiğiniz yerdedir.

## Dünya dönme tabloları {#troubleshooting-earth-rotation-tables}
Yükseklikler, hava kütlesi ve teleskobun güvenlik sınırları Dünya'nın dönüşüne ait tablolara (IERS'ten) ihtiyaç
duyar. Kurulum bir kopyasını getirir; izin verdiyseniz (ilk açılışta ya da **Ayarlar → Dünya dönme tablolarını güncel
tut**) program çevrimiçiyken haftada bir, sessizce, yaklaşık 3 MB'lık yenisini indirir. **Ayarlar → Dünya dönme
tablolarını şimdi güncelle** bunu hemen yapar. Güncelleme olmasa da hiçbir şey çalışmayı bırakmaz: tabloların
öngörüleri yavaşça doğruluk kaybeder (bir yılda birkaç yay saniyesi), bu hava kütlesinin ya da yönelme sınırının
gerektirdiğinin çok altındadır. Gözlem zamanları (BJD) bu tabloları hiç kullanmaz. **Yardım → Kurulumu ve internet servislerini denetle**
kullanılan tabloların yaşını gösterir.

## İnternetsiz çalışmak {#troubleshooting-working-without-internet}

Bir katalog ya da arşivin her yanıtı (Gaia yıldızları, APASS kadirleri, VSX ve ötegezegen efemerisleri, tarama ışık
eğrileri, DSS görüntüleri, bir alandaki asteroitler) ilk kez indirildiğinde bu bilgisayara kaydedilir. Ağ
kesildiğinde kaydedilen yanıt kullanılır. İnternet olmayan bir gözlem yerine gitmeden önce kareleri ve hedefleri
bir kez çevrimiçiyken açın, sonra **Ayarlar → Çevrimdışı çalış** seçeneğini seçin: daha önce indirilen her şey
çalışmaya devam eder, yeni olan her şey önbellekte olmadığını söyler. **Ayarlar → Kaydedilmiş katalog yanıtlarını
sil** yeri boşaltır (en çok 2 GB).

## Güncellemeler {#troubleshooting-updates}
**Yardım → Güncellemeleri denetle…** projenin sürüm sayfasına daha yeni bir sürüm olup olmadığını sorar ve indirme bağlantısını verir. Uygulama bunu kendiliğinden hiç yapmaz. Yeni sürümü eskisinin üstüne kurun; ayarlar, eklentiler ve otomasyonlar korunur.

## Sorun bildirmek {#troubleshooting-reporting-problem}
Ne yaptığınızı, hata metnini not edin ve mümkünse sorunu gösteren küçük bir dosya ekleyin. Proje dosyası her çalıştırmanın tam ayarlarını içerir; sorunu yeniden üretmeye yardım eder.
