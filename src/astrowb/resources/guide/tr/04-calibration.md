# Kalibrasyon
**Kalibrasyon** sayfası ham kareleri kalibre görüntülere çevirir: bias, dark, flat ve light karelerini tanır, master kareleri oluşturur, her light karesine doğru master'ları eşler ve uygular. İsterseniz sonucu hizalayıp birleştirir (yığar). Kalibrasyon kendi penceresinde açılır (Başlangıç sayfasındaki bloğu ya da Pencere menüsü); kendi menüleri vardır; tarama, kalibrasyon ya da yığmanın ilerlemesi durum çubuğunda İptal düğmesiyle görünür.

## 1. Ham kareleri taramak
**İki klasör, bir gecenin genellikle tutulduğu gibi:** light karelerini (verinizi) **Light'lar** alanına, bias, dark ve flat karelerini **BDF** alanına verin. Light klasöründeki her kare, adı ne olursa olsun light'tır — bilim kareleri genellikle yıldızın adıyla kaydedilir (`nsvs01286630_017.fits`); yalnızca başlığı bias, dark ya da flat diyen kare öyle sayılır. BDF klasöründekiler bias, dark ve flat olarak ayrılır. Hepsi tek klasörde mi? Onu yalnızca **BDF** olarak verin, **Light'lar**ı boş bırakın: kareler o zaman aşağıdaki gibi başlığa ve ada göre ayrılır.

Ham karelerin bulunduğu klasörü seçin (light, bias, dark ve flat karışık olabilir, alt klasörler dahil) ve **Tara**'ya basın. Tablo her dosyayı **türü**, **pozu**, **filtresi**, **sıcaklığı** ve **binning**'iyle listeler.

**Gözat…** ya da **Klasör ekle…** ile seçilen klasör hemen taranır; elle yazılan klasörü **Tara** okur.

- Tür `IMAGETYP` / `FRAME` başlığından (Light Frame, Bias, Dark, Flat Field…), yoksa dosya adından anlaşılır. Addaki sözcükler: bias / zero / offset, dark, flat / twilight, arc / lamp; 0 s'lik bir kare bias'tır. Geri kalan her kare **light** sayılır — bilim kareleri genellikle yıldızın adıyla kaydedilir (`nsvs01286630_017.fits`, `NY_Vir_R_003.fit`) ve türünü söylemez; yalnızca başlığın bildirdiği ama programın tanımadığı bir tür (FOCUS, TEST…) **bilinmiyor** olur ve dışarıda bırakılır (tablonun altında listelenir). Tablodaki bir **türe çift tıklayarak** onu değiştirebilirsiniz; dosyalar değişmez. Listeye ait olmayan bir kare (önceki bir çalışmadan kalan bir master, bir deneme karesi) **Listeden çıkar** düğmesiyle ya da Delete tuşuyla çıkarılır; **Temizle** klasörleri ve listeyi boşaltır, klasörleri yeniden seçebilirsiniz. İkisini de Ctrl+Z geri alır.
- Okunamayan ve türü bilinmeyen dosyalar tablonun altında listelenir ve atlanır.
- Aynı liste hangi kalibrasyon karelerinin **eksik** olduğunu söyler, ör. "no flat for filter 'R'" — o light'lar yine kalibre edilir, yalnızca o düzeltme olmadan; bu size bildirilir.

Alt klasörler de okunur. Light'lar ve kalibrasyon kareleri ayrı klasörlerdeyse (örneğin *Light* ve *BDF*) ikisini birden içeren klasörü seçin. Başka bir yerde duran kareler, örneğin bir kalibrasyon arşivi, **Klasör ekle…** ile eklenir (birden çok klasör `;` ile ayrılır). Hiç light karesi bulunamazsa tablonun altındaki liste bunu söyler ve **Kalibre et** bir light olana kadar kapalı kalır.

Arşivlerden gelen ham kareler olduğu gibi kullanılır: ESO'nun `.fits.Z` dosyaları (Unix compress) fits_from_raw klasörüne açılır, ESO kare türleri (DPR TYPE: BIAS, FLAT, STD, WAVE, OBJECT) tanınır ve bir tayfçekerin grizması ya da ağı filtrenin parçası sayılır; böylece başka bir grizmayla alınmış flat asla kullanılmaz.

## Master'lar nasıl eşlenir
- **Bias:** aynı binning ve boyut.
- **Dark:** aynı binning, aynı poz süresi ve 2 °C içinde sıcaklık. Başka pozdaki bir dark, light'ın pozuna yalnızca bias kareleri varsa ölçeklenir (bias çıkarılınca karanlık akım süreyle orantılıdır).
- **Flat:** aynı filtre ve binning; flat'lerden bias/dark çıkarılır ve medyanı 1 olacak şekilde normalleştirilir.
- Her master, karelerinin sigma kırpmalı ortalamasıdır; **Reddetme (sigma)** (varsayılan 3) yalnızca bazı karelerde görünen uyduları, kozmik ışınları ve sıcak pikselleri atar.

## 2. Çıktı klasörü ve seçenekler
Master karelerin ve kalibre görüntülerin yazılacağı yeri seçin. Ham dosyalar hiç değiştirilmez.

- **Light karelerden kozmik ışınları temizle** tek piksellik izleri L.A.Cosmic yöntemiyle (astroscrappy) temizler. Uzun pozlarda kullanın; kısa fotometrik serilerde gerekmez.

- **Dark'ı her ışık karesine ölçekle (dark optimizasyonu):** her ışık karesi için en az gürültüyü bırakan dark ölçeğini bulur (en küçük kareler: sıcak pikseller yok olmalı; yıldızlar ve gök dark ile ilişkili değildir), MaxIm DL'nin otomatik optimizasyonu gibi. Kamera sıcaklığı kaydığında ya da dark'lar başka sıcaklıkta çekildiğinde kullanın; ölçek başlığa yazılır (DARKSCAL).
- **Sıcak ve ölü pikselleri onar (master'lardan kusur haritası):** master dark düzeyinin çok üstündeki (sıcak) ya da master flat düzeyinin yarısının altındaki (ölü, düzeltilemeyecek kadar koyu toz gölgeleri) pikseller her kalibre karede iyi komşularının medyanıyla değiştirilir. Harita master'ların yanına kaydedilir (`defects_00.fits`) ve başlıkta adı yazar (CALDEF).
- **Overscan ve kırpma** karelerin başlığında BIASSEC (overscan şeridi: düzeyi satır satır fit edilir — okuma yönünde kırpmalı kübik, IRAF'ın overscan fiti gibi — ve çıkarılır; okuma boyunca bias yapısı da gider) ve TRIMSEC ya da DATASEC (yalnızca o bölüm tutulur) varsa kendiliğinden yapılır; profesyonel CCD'ler için IRAF ccdproc'un yaptığı gibi.
- **Doğrusallık düzeltmesi** (Diğer kalibrasyon seçenekleri içinde): kameranızın doğrusal olmayışının c0 c1 c2 … katsayılarını yazın, ör. `0 1 4e-6`; her ham değer v, overscan, bias, dark ve flat'ten önce c0 + c1·v + c2·v² + … olur (AstroImageJ'deki gibi). Katsayıları üreticinin belgesinden ya da artan pozlu flatlardan alın (saniye başına sayım sabit kalmalı). Doğrusal bir kamerada boş bırakın. Düzeltilen karelerin başlığında LINCORR olur.

- **Tayf: flat'e bölme:** eşel ve uzun yarık kareleri için işaretleyin. Bunların flat'i order/mertebeler arasında sıfıra yakındır, ona bölmek gürültüyü patlatır (IRAF kullanıcıları böyle bir flat'i önce apflatten / apnormalize ile normalize eder). Bias ve dark yine çıkarılır; master flat yine yapılır — onu Tayf sayfasına verin; mertebeleri onun üzerinde izler ve blaze'ine böler. Kusur haritası o zaman yalnızca dark'tan çıkar.

## 3. Kalibre et
**Kalibre et**'e basın. Görev arka planda çalışır; bitince kaç görüntünün kalibre edildiğini ve kaç master yazıldığını görürsünüz. Her kalibre görüntü hangi master'ların kullanıldığını başlığına yazar (`CALB`, `CALD`, `CALF`); her zaman kontrol edebilirsiniz. Ardından **4. Fotometri sayfasında ölç →** kalibre edilmiş light'ları oraya gönderir ve sayfayı açar (birkaç filtre varsa birini seçersiniz: ışık eğrisi tek filtrede ölçülür). Görüntüler sayfasının sağ tık menüsünde de aynısı vardır: **Açık görüntüleri Fotometriye gönder**.

## 4. Hizala ve birleştir
**Hizala ve birleştir…** kalibre görüntüleri yıldızlara göre hizalar (kayma çapraz korelasyonla bulunur) ve sigma kırpmalı ortalamayla tek derin görüntüde birleştirir. Dosyanın ikinci uzantısına kaydedilen kapsama haritası her piksele kaç karenin katkı verdiğini söyler. Yalnızca aynı filtredeki kareleri birleştirin. Yığma isteğe bağlıdır ve **ışık eğrisi için değildir**: yığının tek bir zamanı vardır, fotometri ise her görüntüyü ayrı ölçer. Derin bir görüntü, sönük cisimlerin astrometrisi ya da renkli görüntü için yığın.

## Birleştirme seçenekleri
Birleştir düğmesinin yanındaki seçenekler Siril, PixInsight ya da MaxIm DL'deki gibi çalışır:

- **Birleştir:** *ortalama* (en az gürültü), *medyan* (sağlam, yaklaşık %25 daha gürültülü) ya da *toplam* (ortalama çarpı kare sayısı; bir karenin örtmediği yerde bile düzey uzun bir pozun düzeyidir).
- **Reddet:** birleştirmeden önce ait olmayan değerleri (uydular, uçaklar, kozmik ışınlar, sıcak pikseller) atar: *sigma kırpma* (IRAF imcombine'ın sigclip'i: medyan ± σ × medyana göre rms dışı, yinelenerek; pikseli on ya da daha çok kare kapsıyorsa. Daha az karede tek bir aykırı değer bu rms'den asla 3 σ uzak düşemez, orada medyan / MAD yayılımı kullanılır), *sigma kırpma, medyan / MAD yayılımı* (her pikselde sağlam yayılım), *winsorized sigma kırpma* (yayılım aykırı değerler içeri çekilerek ölçülür; az karede daha iyi), *min / maks* (her pikselin **Alt** sayıda en düşük ve **Üst** sayıda en yüksek değerini atar) ya da *yüzdelik kırpma* (medyan × (1 − alt) … medyan × (1 + üst) dışı, yüzde olarak; 3–6 kare için). *yok* her şeyi tutar. Yukarıdaki **Reddetme (sigma)** σ'yı ayarlar.
- **Normalize et:** değişen gök altında çekilen kareleri birleştirmeden önce eşitler: *çarpımsal* her karenin gök düzeyini ilk kareninkine ölçekler (ince bulut, airmass/hava kütlesi), *toplamsal* kaydırır (Ay, alacakaranlık düzeyi).
- **Ağırlıklar:** *gürültüye göre* her kareye gök gürültüsünün 1 / σ² ağırlığını verir; kötü kareler daha az sayılır.

- **Hizala:** *yalnızca kaydırma* (çapraz ilinti, hızlı) tek gecenin, montajın tek yönde olduğu kareleri için; *yıldız desenleri* kareler dönmüş ya da ölçeği değişmişse — meridyen dönüşünden sonra, alt-az montajdan ya da döndürücüden, ya da başka bir teleskoptan. En parlak yıldızların üçgenleri eşlenir (kenar oranları dönme ve ölçekle değişmez; Groth 1986, Valdes vd. 1995) ve her karenin dönmesi, ölçeği ve kayması fitlenir; başlıktaki geçmiş bunları listeler.

Birleştirilmiş görüntünün başlığı seçimleri (STACKMTH, STACKNRM, STACKWGT) ve her karenin ağırlığını kaydeder.

## Drizzle
Az örneklenmiş görüntüler (yıldızlar bir iki piksel genişliğinde) kareler arasında küçük dither'larla çekildiyse, birleştirmeden önce **2× ince ızgaraya drizzle**'ı işaretleyin. Her piksel boyutunun %60'ına küçültülüp hizalanmış konumunda iki kat sık bir ızgaraya bırakılır (Fruchter & Hook 2002); sekiz ya da daha çok dither'lı karede yıldızlar normal birleştirmeden daha keskin çıkar. Akı korunur, gök koordinatları (WCS) ölçeklenir ve her çıktı pikselinin ağırlığı ikinci uzantıya yazılır. Önce kalibrasyonda kozmik ışınları temizleyin: drizzle aykırı değerleri ayıklamaz.

## Renkli kameralar ve DSLR ham dosyaları
- Seçilen klasördeki **kamera ham dosyaları** (CR2, CR3, NEF, ARW, DNG, ORF, RW2, RAF, PEF…) **Tara**'ya basınca dönüştürülür: her biri `fits_from_raw` alt klasöründe bir FITS dosyası olur; algılayıcı değerlerine dokunulmaz (beyaz dengesi, gama, ara değerleme yok). Dosyaları `bias`, `darks`, `flats`, `lights` gibi adlı klasörlere koyun: klasör adı kare türünü verir. Poz süresi, ISO, siyah ve beyaz düzeyi dosyadan okunur. Fujifilm X-Trans ve Foveon algılayıcıları 2 × 2 Bayer değildir ve reddedilir.
- **Zaman**: DSLR kendi saatini yazar; bu çoğu zaman yerel saattir ve dakikalarca kaymış olabilir. Taramadan önce **DSLR saati − UTC** değerini girin (ör. Türkiye saatindeki bir saat için 3) ve kamera saatini bir zaman sinyaliyle karşılaştırın: zaman hatası doğrudan minimumlara ve O−C'ye geçer. Asıl okuma DATE-CAM olarak saklanır. Siz girene kadar bilgisayarın kendi UTC farkı kullanılır (kamera bilgisayarla aynı yerel saatteyse doğrudur). Değer hatırlanır ve hangi sayfada açılırsa açılsın (Fotometri, Görüntüler, Değişken yıldız arama…) her kamera ham dosyasına ve telefon resmine uygulanır; Fotometri sayfası karelerinin hangi farkla okunduğunu gösterir.
- **Renkli (tek çekimde renkli) kameralar** BAYERPAT yazar; DSLR dosyaları bunu ham dosyadan alır. **Renkli kamera: her renk ayrı görüntü** seçiliyken (öntanımlı) mozaik olduğu gibi kalibre edilir, sonra her ışık karesi yarı boyutlu üç görüntü olarak yazılır: `_R`, `_G`, `_B` (filtreler TR, TG, TB). Her 2 × 2 hücre için tek değer vardır, yeşil iki yeşil pikselin ortalamasıdır; pikselleri karıştırıp yıldız profillerini değiştirecek ara değerleme yapılmaz. Sıcak ve ölü pikseller aynı renkten piksellerle onarılır. Bu, AAVSO DSLR Gözlem El Kitabı'nın yöntemidir; yeşil kanal (TG) Johnson V'ye en yakın olandır, bu yüzden Fotometri sayfasına o gider.
- **Yığınlar filtre başına yapılır**: `stack_TR.fits`, `stack_TG.fits`, `stack_TB.fits` (tek renkli kameralarda da her filtre için bir tane). Renkli resim için **Görüntü → Üç filtreden renkli görüntü…** ile birleştirin.

## İpuçları
- Light'larla aynı sıcaklıkta en az 20 bias ve 10–20 dark alın; filtre başına 10–20 flat, ortalaması tam kuyu kapasitesinin yarısı civarında olsun.
- Flat'lerle light'lar arasında odaklayıcıyı oynatmayın, kamerayı döndürmeyin: toz halkaları onlarla birlikte kayar.
- *Gece sonu kalibrasyonu ve yığma* otomasyonu tarama, kalibrasyon ve yığmayı tek seferde yapar.
