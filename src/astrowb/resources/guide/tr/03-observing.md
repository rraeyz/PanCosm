# Gözlem ve güvenlik
**Gözlem** sayfası teleskobu, kamerayı, odaklayıcıyı, filtre tekerini, kubbeyi ve kılavuzlamayı denetler. Cihazlar güvenlik denetçisi olan ayrı bir **gözlemevi sürecine** aittir; pencere kapansa ya da çökse bile teleskop korunur. Kendi penceresinde açılır (Başlangıç sayfasındaki bloğu ya da Pencere menüsü); kendi menüleri vardır.

## Gözlemevini yapılandırmak
**Gözlemevini kur…** aşağıdakilerin hepsi için bir pencere açar: gözlem yeri, cihazlar (**Ağdaki Alpaca cihazlarını bul** yanıt veren her ASCOM Alpaca cihazını listeler; INDI cihazları sunucu adresi ve INDI cihaz adıyla elle eklenir), güvenlik sınırları, PHD2 ve başka bilgisayarların bağlanıp bağlanamayacağı. Riskli seçimlerde uyarır, ör. hava sensörü olmayan bir kundak. **Kaydet ve başlat** dosyayı yazar ve gözlemevini bu bilgisayarda başlatır; **Aç…** var olan bir dosyayı düzenler.

Yazdığı dosya düz JSON'dur, elle de düzenlenebilir:

```json
{
  "site": {"lat": 39.9, "lon": 32.8, "height": 900},
  "devices": {
    "mount": {"alpaca": "127.0.0.1:11111", "number": 0},
    "camera": {"alpaca": "127.0.0.1:11111", "number": 0},
    "filterwheel": {"alpaca": "127.0.0.1:11111"},
    "focuser": {"indi": "127.0.0.1:7624", "device": "Focuser Simulator"},
    "dome": {"alpaca": "127.0.0.1:11111"},
    "monitor": {"alpaca": "127.0.0.1:11111"}
  },
  "rules": {"min_alt": 20, "max_humidity": 85, "max_wind": 10},
  "phd2": {"host": "127.0.0.1", "port": 4400},
  "listen": "127.0.0.1:11112"
}
```

- Her cihaz ya **ASCOM Alpaca** (`"alpaca": "adres:port"` ve cihaz numarası) ya da **INDI**'dir (`"indi": "adres:port"` ve INDI cihaz adı). Windows'taki klasik ASCOM sürücülerine ASCOM Remote (Alpaca) üzerinden ulaşılır.
- `monitor` bir güvenlik izleyicisidir (bulut/yağmur sensörü), `conditions` bir gözlem koşulları cihazıdır (nem, rüzgâr, yağmur, bulut).
- `listen` gözlemevi API'sinin adresidir. Başka bir bilgisayardan denetlemek istemiyorsanız `127.0.0.1` olarak bırakın.

## Başlatmak ve bağlanmak
- **Gözlemevini bu bilgisayarda başlat…** yapılandırma dosyasını sorar, gözlemevi sürecini arka planda başlatır ve bağlanır. İlk seferde gizli bir **erişim anahtarı** (token) oluşturulup dosyaya yazılır.
- Uzaktaki bir gözlemevi için orada `--observatory config.json` ile başlatın, sonra burada **Gözlemevi adresi** ve **Erişim anahtarı**nı yazıp **Bağlan**'a basın.
- **HTTPS:** kurulumda *Bağlantıyı şifrele*'yi işaretleyin (başka bilgisayarların bağlanmasına izin verince kendiliğinden işaretlenir). Gözlemevi kendi sertifikasını üretir ve başlarken **parmak izini** yazar; denetlediğiniz bilgisayarda bunu *Sertifika parmak izi* alanına yazın ve `https://` adresi kullanın. Uygulama yalnızca tam olarak o sertifikaya sahip gözlemeviyle konuşur; aradaki kimse erişim anahtarını ya da komutları okuyamaz. Aynı bilgisayarda parmak izi kendiliğinden doldurulur.
- Renkli satır durumu gösterir: **Güvenli** (yeşil), nedenleriyle **GÜVENLİ DEĞİL** (kırmızı) ya da **bağlantı yok**.

## Güvenlik denetçisi
Denetçi birkaç saniyede bir kuralları denetler. Herhangi bir şey güvensizse **pozlamayı keser, sekansı durdurur, kundağı park eder ve kubbeyi kapatır**. Güvensiz konumlara yönelmeyi de reddeder. Kurallar (yapılandırmadaki `"rules"`):

- `min_alt` (15°) ve isteğe bağlı bir `horizon` (ufuk) profili `[[az, irtifa], …]`;
- `sun_max_alt` (−6°): Güneş bunun üstündeyse gündüzdür — gün doğarken teleskop park edilir ve kubbe kapanır;
- `sun_min_sep` (30°): hedefle Güneş arasındaki en küçük açı;
- `max_humidity` (%90), `max_wind` (12 m/sn), `max_rain_rate` (her yağmur), `max_cloud_cover`;
- `link_timeout_s` (30 sn): yanıt vermeyen cihaz güvensiz sayılır.

Güvensiz bir dönemden sonra hiçbir şey kendiliğinden yeniden başlamaz: teleskobu kontrol edin ve **Devam et**'e basın (hâlâ güvensizse reddedilir).

## Teleskobu hareket ettirmek
Koordinatı yazın (`02:04:10 +46:41:16`) ve **Yönel**'e basın. Yanında **Park et**, **Durdur** (her şeyi hemen durdurur), **Devam et** ve **Otomatik odak** vardır. Kundak satırı irtifayı, azimutu ve izleyip izlemediğini ya da park hâlinde olduğunu gösterir.

**Ortala** hedefi tam ortaya getirir: gözlemevi yönelir, kısa bir kare çeker, plaka çözer, kundağa gerçekte nereye baktığını söyler (sync) ve yeniden yönelir; hedef 30″ içine girene kadar. Gözlemevi bilgisayarında ASTAP ya da astrometry.net gerekir.

**Kutup hizalama** ekvatoral kundağın RA ekseninin gök kutbundan ne kadar saptığını ölçer: kabaca kuzeye (güney yarıkürede güneye), dik açıklık 60–80°'ye yönelin ve düğmeye basın; yalnızca RA ekseni 30°'lik adımlarla dönerken çözülen üç kare çekilir. Sonuç ekseni ne kadar yükseltmeniz ya da indirmeniz ve doğuya ya da batıya ne kadar çevirmeniz gerektiğini yay dakikası olarak söyler. Ayarlayıp hata birkaç yay dakikasına inene kadar yeniden ölçün.

## Kamera, odaklayıcı ve filtre
- **Önizleme:** verilen süre ve seçili filtreyle tek poz; çıktı klasörünün `preview` alt klasörüne kaydedilir ve hemen görüntüleyicide açılır (kadraj ve odak için). Gözlemevi başka bir bilgisayardaysa kare önce buraya, ev klasörünüzdeki `observations/preview` içine kopyalanır.
- **Soğutucu:** **Soğut** kamera sıcaklığını ayarlar ve soğutucuyu açar; **Kapat** kapatır. Geceden önce yavaş soğutun, kamerayı kapatmadan önce ısıtın.
- **Odaklayıcı:** **Taşı** odaklayıcıyı mutlak bir konuma götürür.
- **Filtre:** liste filtre tekerinden okunur; **Değiştir** tekeri çevirir.
- Gri satır kamera sıcaklığını ve soğutucu durumunu, odaklayıcı konumunu ve geçerli filtreyi gösterir.

## Otomatik odak
**Otomatik odak** birkaç odaklayıcı konumunda kare alır, yıldızların yarı akı yarıçapını (HFR) ölçer ve bir V eğrisi fit eder; odaklayıcı en iyi konuma götürülür. Önce yıldızlı bir alana yönelin.

## Sekanslar
Sağ tarafta:

- **Hedef adı** ve **RA Dec** (dark ve bias için koordinatı boş bırakın: yönelme olmaz).
- **Her N karede dither (PHD2):** kareler arasında yönelimi PHD2 ile biraz kaydırır; sıcak pikseller ve sabit desenler ortalamada yok olur.
- **Başlangıç:** şimdi için boş, `dusk` (akşam karanlığı) ya da `2026-11-15T21:30` gibi bir UTC zamanı. **Bitiş:** adetler bitince durmak için boş, `dawn` (şafak) ya da bir UTC zamanı — bitiş verilirse poz listesi **o zamana kadar tekrarlanır** (bir örtme ya da bütün gece boyunca zaman serisi).
- **Kayıt yeri:** gözlemevi bilgisayarındaki klasör.
- Poz tablosu: **Tür** (light, dark, bias, flat), **Filtre**, **Poz (sn)**, **Adet**, **Binning**. **Poz satırı ekle** / **Satırı kaldır**.
- **Çekim sırasını başlat.** İlerleme ve yazılan kare sayısı tablonun altında görünür; soldaki günlük her olayı listeler.

Gözlemevi başka bir bilgisayardaysa, biten bir sekansın kareleri bu bilgisayara, ev klasörünüzdeki `observations/<Kayıt yeri klasörünün son parçası>` içine kopyalanır. Gözlemevi yalnızca kendi kaydettiği kareleri verir; o bilgisayardaki başka hiçbir dosya ağdan okunamaz.

Her kare, sonraki adımların gerektirdiği başlıklarla FITS olarak kaydedilir: tür, poz, başlangıç zamanı (UTC), filtre, binning, sıcaklık, kazanç, cisim ve koordinatlar, gözlem yeri.

## Meridyen dönüşü ve kılavuzlama
Alman ekvatoral kundaklar hedef meridyeni geçince kendiliğinden döndürülür; kılavuzlama dönüş sırasında durdurulup yeniden başlatılır. Kılavuzlama ve dither **PHD2** ile yapılır (`"phd2"` ayarı).

## Gökyüzü flatları
İstediğiniz filtre ve adetin olduğu satırı seçin, teleskobu flat noktasına çevirin (izleme kapalı) ve **Gökyüzü flatları**'na basın. Alacakaranlıkta poz süresi gök parlaklığını izler; her flat iyi bir düzeye ulaşır.

## Gözetimsiz bir gece
Hedeflere başlangıç olarak `dusk`, bitiş olarak `dawn` verin. Sekans karanlığı bekler, şafağa kadar tekrarlar; denetçi gün doğarken ya da hava bozulunca teleskobu park eder. *Örten çift gecesi* ve *Gece sonu kalibrasyonu* otomasyon şablonları sekansı sizin için doldurur.

## Önce simülatörle deneyin
Gerçek cihazlardan önce aynı yapılandırmayı simülatörlerle çalıştırın (ASCOM Alpaca simülatörleri ya da INDI simülatör sürücüleriyle `indiserver`). Güvensiz koşulların kundağı park edip kubbeyi kapattığını görün.

## Kamera ayarları, odak ofsetleri, rotator ve düz alan paneli
Her poz satırında **Kazanç**, **Ofset**, **Okuma modu** (kameranın listesindeki sırası) ve birleştirilmiş piksel cinsinden **Alt kare** `x, y, genişlik, yükseklik` vardır. Boş hücreler kameranın kendi ayarını ve tam kareyi korur. Değerler her FITS başlığına yazılır (GAIN, OFFSET, READOUTM, XORGSUBF/YORGSUBF). Dark, bias ve flatları ışık kareleriyle aynı kazanç, ofset ve alt karede çekin; yoksa kalibrasyon onları eşleştiremez.

**Filtre odak ofsetleri** ve **sıcaklık düzeltmesi** *Gözlemevini kur…* penceresinde ayarlanır: ofsetler `L=0, B=-30, V=15` biçiminde (odaklayıcı adımı; filtre değişince odaklayıcı farkı kadar hareket eder), katsayı °C başına adım (iki sıcaklıkta odaklayarak ölçün). Sekans sırasında odaklayıcı, kendi sıcaklığı 0,5 °C değiştikçe onu izler.

Bir **rotator** (ASCOM Alpaca) yönelmeden önce hedefin **Rotator açısına** döner; açı ROTATANG olarak yazılır.

**Panel flatları** bir Alpaca *CoverCalibrator* (açılır kapaklı ya da ışıklı panel) kullanır: kapak kapanır, panel yanar, kareler hedef düzeye ulaşana kadar poz süresi ayarlanır ve sonunda panel kapatılır. Filtre ve flat sayısı seçili satırdan alınır.
