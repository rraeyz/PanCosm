# Sorun giderme
Sık karşılaşılan sorunlar ve yapılacaklar.

## Bir görev başarısız oldu
Görevler paneli *başarısız* gösterir ve bir pencere hatayı verir. Tipik nedenler: okunamayan bir dosya, eksik bir girdi (ileti adını söyler), çok az yıldız ya da kare. Pencere kullanılabilir kalır; girdiyi düzeltip adımı yeniden çalıştırın. Projenin geçmişi başarısız çalıştırmayı ayarlarıyla saklar.

## Kalibrasyon karelerin eksik olduğunu söylüyor
"no flat for filter …", "no dark for … s", "no bias" — o light'lar yine o düzeltme olmadan kalibre edilir. Eksik kareleri alın (aynı filtre, binning, poz ve sıcaklık) ya da sonucu kabul edin. Başka pozdaki dark'lar yalnızca bias kareleriyle kullanılabilir.

## Yıldızlar bulunmuyor ya da ışık eğrisi sıçrıyor
- Görüntülerin kalibre ve tek filtreden olduğundan emin olun.
- Odak dışı ya da iz bırakan yıldızlar için açıklığı büyütün; gök halkasını komşulardan uzaklaştırın.
- Alan çok kayıyorsa hedefin her karede içeride olduğunu kontrol edin; olmadığı kareler atlanır.
- Başka karşılaştırma yıldızları seçin: biri değişken ya da doymuş olabilir.

## Zamanlar yanlış görünüyor
Başlıktaki `DATE-OBS`'u (pozun UTC başlangıcı olmalı) ve `EXPTIME`'ı kontrol edin. BJD için hedefin koordinatları ve gözlem yeri bilinmelidir (başlıkta ya da sayfadaki alanlarda).

## Plaka çözümü bir şey yapmıyor
ASTAP'ı bir yıldız veritabanıyla (ya da astrometry.net'i indeks dosyalarıyla) kurun ve yeniden deneyin. Başlıktaki yaklaşık koordinatlar işi çok hızlandırır. Çok küçük alanlar daha derin bir veritabanı ister.

## Gözlemevi GÜVENLİ DEĞİL diyor
Nedenler listelenir: Güneş doğmuş, hedef çok alçak, nem, rüzgâr, yağmur, yanıt vermeyen bir cihaz… Nedeni giderin, sonra **Devam et**'e basın. Bir şey hâlâ güvensizken Devam et reddedilir — bu bilerek böyledir.

## Gözlemeviyle bağlantı yok
Gözlemevi sürecinin çalıştığını (**Gözlemevini bu bilgisayarda başlat…** ile yeniden başlatın), adresi ve erişim anahtarını kontrol edin. Uzak bir bilgisayarda güvenlik duvarı portu engelliyor olabilir.

## Ekran kartı kullanılmıyor
**Ayarlar → İşlem birimi** kipi gösterir; durum çubuğu birimin adını verir. *Otomatik* kipte kart yalnızca daha hızlıysa kullanılır. Kart bulunmuyorsa ekran kartı sürücüsünü güncelleyin; her şey işlemcide de çalışır.

## Ayarlarım ve dosyalarım nerede?
Ayarlar, eklentiler ve otomasyonlar kullanıcı ayar klasöründedir (Linux'ta `~/.config/…`, Windows'ta `%LOCALAPPDATA%\…`, macOS'ta `~/Library/Application Support/…`). Projeler ve sonuçlar sizin kaydettiğiniz yerdedir.

## Güncellemeler
**Yardım → Güncellemeleri denetle…** projenin sürüm sayfasına daha yeni bir sürüm olup olmadığını sorar ve indirme bağlantısını verir. Uygulama bunu kendiliğinden hiç yapmaz. Yeni sürümü eskisinin üstüne kurun; ayarlar, eklentiler ve otomasyonlar korunur.

## Sorun bildirmek
Ne yaptığınızı, hata metnini not edin ve mümkünse sorunu gösteren küçük bir dosya ekleyin. Proje dosyası her çalıştırmanın tam ayarlarını içerir; sorunu yeniden üretmeye yardım eder.
