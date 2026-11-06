# Fotometri
**Fotometri** sayfası bir dizi kalibre görüntüde hedef yıldızın parlaklığını karşılaştırma yıldızlarına göre ölçer; ışık eğrisi, minimum zamanları ve raporlar verir.

## Görüntüleri ve yıldızları seçmek
1. **Görüntüleri seç…** — tek alanın ve tek filtrenin kalibre kareleri. Zamana göre sıralanırlar.
2. İlk görüntüde **önce hedef yıldıza**, sonra **bir ya da daha fazla karşılaştırma yıldızına** tıklayın. Tıklama yıldızın merkezine oturur. **Yıldızları temizle** baştan başlatır.
3. Ya da **Karşılaştırma yıldızı öner**'e basın: parlaklığı benzer, doymamış, parlak komşusu olmayan ve her görüntüde çerçevenin içinde kalan yıldızları seçer. Ölçmeden önce kontrol edin.

İyi karşılaştırma yıldızlarının rengi ve parlaklığı hedefe benzer ve değişken değildir. Birkaç tane kullanın: toplamları (topluluk) tek yıldızdan daha az gürültülüdür.

Görüntünün üzerinde imleç artı işaretidir; bir sonraki tıklamanın koyacağı açıklık ve gök halkası, işaretleyeceği yıldızın renginde (yeşil hedef, kırmızı karşılaştırma, turuncu kontrol yıldızı) imleci izler. Zaten işaretli bir yıldıza tıklamak işareti kaldırır. Görüntüyü kaydırmak için sürükleyin, yakınlaştırmak için tekerleği kullanın.

**Her kare:** görüntü sayısının altındaki oklar ve kaydırıcı kareleri zaman sırasıyla, her karenin adı ve zamanıyla gösterir. Yıldızları en iyi görünen karede işaretleyin: konumlar o kareye aittir, ölçüm onları öteki karelere taşır (kareler arasındaki kayma ölçülür, her yıldız yeniden ortalanır). İşaretli yıldızlar yalnızca o karede çizilir. Bir kareyi dışarıda bırakmak için (bulut, uydu izi, kötü odak) **Bu kareyi kullan** işaretini kaldırın.

TESS ve Kepler / K2 hedef piksel dosyaları ile MAST'tan TESScut kesitleri olduğu gibi seçilebilir: her kadans bir kare olur (görevin işe yaramaz diye işaretlediği kadanslar dışarıda kalır) ve arşivin BJD_TDB zamanını taşır. Bölünecek bir atmosfer olmadığından hedef **karşılaştırma yıldızı olmadan** ölçülebilir: bağıl akı o zaman hedefin kendi akısının medyanına oranıdır.

## Diferansiyel fotometri: hedefler, mukayese ve kontrol yıldızları
**Tıklamalar ekler** sonraki tıklamaların ne olacağını seçer: *hedef, sonra mukayese yıldızları* (ilk tıklama hedef T1, sonrakiler mukayese yıldızları C1, C2…), *kontrol yıldızları* (K1, K2…) ya da *başka hedefler* (T2, T3…). Kontrol yıldızları ve diğer hedefler her karede aynı mukayese yıldızlarına göre ölçülür ama onlara katılmaz — MaxIm DL, VPhot ya da AIJ'deki kontrol yıldızı gibi. Sabit bir kontrol yıldızı fotometrinin gerçekte ne kadar iyi olduğunu gösterir: saçılması (mmag) grafiğin altında yazılır.

**Yıldızlar** sekmesi her yıldızı görevi ve konumuyla listeler. Mukayese yıldızlarının **bilinen kadirlerini** (AAVSO haritasından, bir katalogdan ya da kendi kalibrasyonunuzdan) son sütuna yazın: hedef, diğer hedefler ve kontrol yıldızları kare kare **kadir** olarak çıkar (her mukayese yıldızı bir sıfır noktası verir; 0,1 kadirden fazla uyuşmayan mukayese yıldızı dışarıda bırakılır ve adı yazılır). **Standart kadirler (APASS / Gaia)** aynı sütunu kataloglardan doldurur.

**Mukayese yıldızlarını saçılmalarına göre ağırlıklandır:** her mukayese yıldızı diğerlerinin toplamına göre ölçülür ve varyansının tersiyle ağırlıklandırılır (yinelenerek; böylece değişen bir mukayese yıldızı diğerlerinin saçılmasını bozamaz). Değişen ya da bozuk bir mukayese yıldızı o zaman neredeyse hiç sayılmaz.

**Grafik** sekmesi neyin çizileceğini seçer: T1 göreli akısı, diferansiyel kadiri Δm = −2,5 log(hedef / topluluk), kadiri, her diğer hedef ya da kontrol yıldızı, **mukayese yıldızlarının birbirine göre eğrileri** (değişen olan hemen göze çarpar), **bütün yıldızlar normalize ve kaydırılmış**, ya da zamana karşı airmass/hava kütlesi, gök, FWHM ve konum. Bir yıldızın doyma düzeyine ulaştığı kareler kırmızı daireyle işaretlenir ve sayılır.

## Kare kalitesi
**Kare kalitesini denetle** seçilen her kareyi ölçer: yıldızların boyutu (FWHM), kaç yıldız göründüğü ve gökyüzü düzeyi. Grafik bu üçünü gece boyunca gösterir; gecenin olağan karesinden çok daha kötü olanlar nedeniyle kırmızı işaretlenir — *yıldızlar bulanık* (rüzgâr, odak, seeing), *az yıldız* ya da *yıldız yok* (bulut, çiy), *gökyüzü parlak* (alacakaranlık, Ay). **Kötü kareleri dışarıda bırak** onları ölçmeden önce çıkarır. *Örten çift gecesi* ve *Ötegezegen geçişi* otomasyonları bunu kendiliğinden yapar.

## Açıklıklar
Her yıldızın görüntü üzerinde çizilen üç halkası vardır: **açıklık** (düz çizgi) ile **gök halkasının** iç ve dış kenarı (kesikli). Yarıçaplar görüntü pikseli cinsindendir; halkalar yakınlaştırınca büyür, uzaklaştırınca küçülür: yakınlaştırıp yıldızın 1. halkanın içinde, 2. ile 3. halka arasında yalnız gökyüzü olduğunu görün. Görüntü üzerinde **Shift + fare tekerleği** üç halkayı birlikte büyütür ya da küçültür (0,5 piksel); sağdaki kutular sayıları gösterir. Çok uzaklaştırılmış bir karede, halkalar birkaç ekran pikselinden küçük kalınca her yıldız küçük bir artıyla gösterilir.

- **1. halka, açıklık:** yıldızın ışığının toplandığı daire.
- **1. ve 2. halka arası:** bilerek dışarıda bırakılır. Burada yıldızın kanatları (dış ışığı) bulunur; ölçülse gök olduğundan parlak görünürdü.
- **2. ve 3. halka arası, gök halkası:** gök düzeyi burada ölçülür (sigma kırpmalı medyan; sönük komşular ve sıcak pikseller sayılmaz) ve açıklıktaki her pikselden çıkarılır.

**Yarıçapları yıldız profillerinden seç**, tıkladığınız yıldızlardan üç halkayı belirler; diğer programların seeing/görüş profiliyle (AstroImageJ) ya da büyüme eğrisiyle (DAOPHOT) yaptığı gibi:

1. Yıldızların **FWHM**'si ışınsal profillerinden ölçülür (Moffat fiti).
2. **Açıklık**, ışık eğrisinin sinyal/gürültüsünün en iyi olduğu yarıçaptır: hedef ve mukayese yıldızlarının büyüme eğrisi üzerinde CCD denklemi (yıldızın foton gürültüsü, her pikseldeki gök ve okuma gürültüsü) her yarıçapta hesaplanır (Howell 1989). Sönük yıldızların en iyi S/G'si küçük, parlak yıldızlarınki daha büyük açıklıktadır. 1 ile 3 FWHM arasında tutulur: daha küçük açıklıklar ışığın seeing/görüşe bağlı bir kısmını kaybeder ve merkezleme hatalarından etkilenir.
3. **Gök halkasının iç yarıçapı**, seçilen en parlak yıldızın ışığının %99,5'inin toplandığı yerdir ve en az 3 FWHM'dir: gerçek yıldızların kanatları vardır ve seeing/görüş gece boyunca değişir.
4. **Dış yarıçap**, halkayı piksel olarak açıklığın dört katı yapar; böylece gök, sonuçtaki kendi gürültüsüne yalnızca %25 ekler (Merline & Howell 1995).

Grafik yıldızın profilini açıklık (yeşil), dışarıda bırakılan boşluk ve gök halkası (mavi) ile gösterir; altındaki satır sayıları verir. Yarıçapları yine de elle değiştirebilirsiniz.

- **Yarıçaplar seeing/görüşü izlesin:** her karede üç yarıçap da o karenin FWHM'sinin ilk karenin FWHM'sine oranıyla ölçeklenir (AstroImageJ'deki "değişken açıklık"). Böylece açıklık hep ışığın aynı kısmını içerir; görüşün çok değiştiği ya da odağın kaydığı gecelerde işe yarar.
- Odak dışı yıldızlarda (halka ya da düz disk) profile bakın: FWHM o zaman diski ölçer ve yarıçaplar ona uyar.
- Yıldızlar her karede yeniden merkezlenir ve alanın gece boyunca kayması kareden kareye izlenir.
- Otomasyon şablonları yarıçapları kendiliğinden bu yolla seçer.

## Zaman ve BJD
Zamanlar `DATE-OBS` ve `EXPTIME`'dan alınır (pozun ortası). **Hedef RA Dec** (ya da başlıktaki `OBJCTRA`/`OBJCTDEC`) ve başlıktaki gözlem yeri ile zamanlar, örtme ve geçiş zamanlamasının standardı olan **BJD_TDB**'ye çevrilir.

## Işık eğrisini ölçmek
**Işık eğrisini ölç** arka planda çalışır ve göreli akıyı (hedef / karşılaştırma topluluğu) zamana karşı çizer. Grafiğin altında nokta sayısı ve yüzde olarak saçılım yazar. Ölçülemeyen karelerin (bulut, yıldız dışarıda) noktaları atlanır ve bildirilir.


**Sintilasyon:** yıldızın atmosferde titreşmesi, foton istatistiğinin bilmediği bir gürültü ekler; parlak yıldızlarda ve kısa pozlarda en büyük hatadır. **Teleskop açıklığı (m)** girilirse (ya da başlıkta mm cinsinden APTDIA varsa) ve gözlem yeri ile hedefin konumu biliniyorsa, her akı hatasına eklenir — σ² = 10⁻⁵ · 1,5² · D^(−4/3) · t⁻¹ · X³ · e^(−2h/8000 m) (Osborn vd. 2015, Young 1967'nin düzeltilmiş hâli; D açıklık, t poz, X airmass/hava kütlesi, h yükseklik). Grafiğin altındaki satır eklenip eklenmediğini ve ne kadar olduğunu (kare başına mmag) yazar. Ölçülen akılar değişmez, yalnızca hata çubukları.

## Kötü noktaları silmek ve eğrileri aralamak
**Grafik** sekmesinde **Silmek için noktaya tıkla**'yı işaretleyip ışık eğrisinin bir noktasına tıklayın (bulut, uydu, yıldızın kaybolduğu bir kare): o kare ışık eğrisinden, kadirlerden, detrendden, minimum zamanından ve dışa aktarmadan çıkarılır. **Silinen noktaları geri getir** hepsini geri getirir. **Eğriler arası aralık**, birden çok eğrili görünümlerde (*bütün yıldızlar*, *mukayese yıldızları birbirine göre*) eğrilerin ne kadar aralıklı çizileceğini ayarlar; 0 hepsini üst üste koyar — örneğin iki standart yıldızın aynı düz çizgiyi verdiğini görmek için.

Programdaki her grafiğin araç çubuğunda **Ayrı pencerede aç** vardır: grafiğin bir kopyası kendi penceresinde açılır; çalışmaya devam ederken büyük hâliyle inceleyebilirsiniz (yakınlaştırma, kaydırma, kaydetme).

## Detrend (eğilim giderme)
Yıldızın kendisinden gelmeyen yavaş değişimler — airmass/hava kütlesiyle değişen sönümleme, kayan gök, odak ya da yıldızın çip üzerinde kayması — bölünerek giderilebilir (AstroImageJ ya da EXOTIC'teki gibi). **Grafik** sekmesinde neye göre detrend edileceğini işaretleyin (hava kütlesi, FWHM, gök, x, y, zaman), olayın kendisi fitlenmesin diye tutulmanın ya da geçişin başlangıç ve bitişini **Dışarıda bırak** alanlarına yazın ve **Detrend et**'e basın: ln(akı) bu aralığın dışındaki noktalarda işaretli büyüklüklere doğrusal olarak fitlenir ve bütün noktalardan bölünerek çıkarılır. Grafiğin altındaki satır önceki ve sonraki saçılmayı verir. **Detrendi geri al** ölçülen eğriye döner. FWHM, *Yarıçaplar seeing/görüşü izlesin* açıkken vardır; hava kütlesi için yer ve hedefin konumu gerekir. Minimum zamanı, dışa aktarma ve AAVSO raporu detrend edilmiş eğriyi kullanır.

**Eğilim derecesi** 1 işaretli her niceliğe doğrusal bağımlılığı böler; 2 ya da 3 eğri fit eder (ör. airmass/hava kütlesiyle doğrusal olmayan sönümleme ya da zamanda bükülen yavaş bir kayma). Eğilimi gideren en düşük dereceyi kullanın: yüksek derece uzun bir örtmeyi de bükebilir.

## Minimum zamanı
- Biliyorsanız **Efemeris T0 (BJD)** ve **Periyot (gün)** girin (isteğe bağlı): o zaman çevrim ve O-C de verilir.
- **Ne tür bir minimum?** altında **Örten çift yıldız: Kwee–van Woerden yöntemi** (varsayılan; Kwee & van Woerden 1956, O−C veritabanlarının yöntemi) ya da düz tabanlı düşüşlere uyan ve derinlik ile süreyi de veren **Ötegezegen geçişi: yamuk fiti** seçin.
- **Minimum zamanı** zamanı hatasıyla (KvW için KvW ve bootstrap hatalarının büyüğü) gün ve dakika olarak verir.
- Işık eğrisi birden çok tutulmayı kapsıyorsa (TESS, birkaç gece) T0'ı ve dönemi girin — bu ışık eğrisinde **Dönem arama** yaptıysanız kendiliğinden dolar — her birincil ve ikincil minimum kendi penceresinde zamanlanır ve türüyle O-C sayfasına gönderilir; bunlar verilmezse sayfa anlamsız tek bir zaman vermek yerine onları ister.

## Standart kadirler
İlk görüntü plaka çözümlüyse (Görüntü → Plaka çözümü), görüntülerinizin filtresini seçip **Standart kadirler (APASS / Gaia)**'ya basın. Mukayese yıldızları internetten aranır: B, V, g′, r′, i′ APASS DR9'dan gelir; R ve I (ve APASS'ta değeri olmayan V) Gaia DR3'ten yayımlanmış Gaia–Johnson-Cousins bağıntılarıyla hesaplanır (yaklaşık 0,03 kadir saçılım); G Gaia'nın kendi kadiridir. Işık eğrisi bunun üzerine standart sistemde kadire döner: her kare için bütün mukayese yıldızlarından bir sıfır noktası ve, üç ya da daha çok mukayese yıldızının rengi varsa, gece için fit edilen bir renk terimi. Katalogla 0,1 kadirden fazla uyuşmayan bir mukayese yıldızı (değişken, karışmış ya da hatalı katalog değeri) bildirilir ve dışarıda bırakılır. Kadirler çizilir (parlak yukarıda), CSV çıktısına girer ve AAVSO raporundaki mukayese kadirlerini doldurur.

## Dışa aktarmak
- **CSV olarak dışa aktar…** zamanı, göreli akıyı, Δm'yi ve hatalarını, biliniyorsa kadirleri, her kontrol yıldızını ve diğer hedefi, ham akıları, airmass/hava kütlesini ve FWHM'yi başka programlar için yazar.
- **AAVSO raporu dışa aktar…** AAVSO genişletilmiş biçimini yazar: yıldız adı (VSX'teki gibi), gözlemci kodunuz, filtre, karşılaştırma yıldızlarının katalog kadirleri, harita kimliği (Chart ID) ve notlar; ilk kontrol yıldızı, AAVSO'nun topluluk fotometrisi için istediği gibi KNAME / KMAG alanlarına yazılır.

## Canlı ışık eğrisi
(**Diğer araçlar** altında) **Canlı: gece boyunca bir klasörü izle…** kameranın yazdığı klasörü izler. Her yeni kare geldikçe kalibre edilir (seçtiğiniz master'larla ya da master'sız) ve ölçülür; ışık eğrisi kendiliğinden büyür. Başlamadan önce ilk karede hedefe ve karşılaştırma yıldızlarına tıklayın. Ölçülemeyen kareler atlanır ve sayılır.

## Polarimetri (çift demet)
(**Diğer araçlar** altında) Çift demetli polarimetre (Wollaston prizması + yarım dalga plakası) için: yıldızın **sıradan** görüntüsüne hedef olarak, **sıra dışı** görüntüsüne ilk karşılaştırma olarak tıklayın, sonra **Polarimetri (çift demet)**. Yarım dalga plakası açısı başlıktan okunur. Sonuç Stokes q ve u, kutuplanma derecesi P (yanlılığı giderilmiş hali de) ve θ açısıdır, hatalarıyla.

## PSF fotometrisi ve değişen yıldız arama
**PSF fotometrisi** (Fotometri sayfasında işaretleyin) açıklık içini toplamak yerine her karenin FWHM'sindeki bir yıldız görüntüsünü her yıldıza fit eder; 2,5 FWHM'den yakın yıldızlar birlikte fit edilir, böylece iç içe komşunun ışığı hedefe karışmaz. Kalabalık alanlarda (kümeler, Samanyolu) kullanın; seyrek alanlarda açıklık da aynı iyiliktedir.

**Işık eğrileri ve O-C → Değişen yıldız arama** ilk karedeki her yıldızı bütün karelerde ölçer (açıklık ya da PSF), sabit yıldızlardan her kareye ortak sıfır noktası verir (bulut ve airmass/hava kütlesi birbirini götürür) ve her yıldızın saçılmasını parlaklığına karşı çizer. Sabit yıldızlar sönüğe doğru yükselen bir eğriyi izler (foton gürültüsü); bunun belirgin üstündekiler **aday**dır (kırmızı halkalar, indekse göre listelenir). Bir noktaya ya da satıra tıklayınca o yıldızın ışık eğrisi görünür; **Bu yıldızı Periyot aramaya gönder** ile periyodunu bulun. Muniwin'in *varfind* aracının yaptığı budur: keşif duyurmadan önce adayları VSX'te denetleyin.

## Sönümleme ve dönüşüm katsayıları
**Görüntü → Fotometrik katsayılar…**
- **Gecenin sönümlemesi:** ölçtüğünüz ışık eğrisinin mukayese yıldızlarından (kareler gök konumunu vermeli ki airmass/hava kütlesi bilinsin): her yıldızın aletsel kadiri hava kütlesine karşı, hepsi için tek eğim k (kadir / hava kütlesi), Bouguer grafiğiyle. İyi bir yerde V'de tipik değer 0,15–0,3.
- **Dönüşüm katsayıları:** bir standart alanın (ör. bir Landolt alanı ya da M67) iki filtrede plaka çözülmüş iki görüntüsü. Yıldızlar ikisinde de ölçülür, kadirleri APASS'tan (B, V, g′, r′, i′) ya da Gaia'dan (V, R, I) gelir ve katsayılar AAVSO düzeninde fit edilir: (b−v)'ye karşı (B−V)'den Tbv, (B−V)'ye karşı V−v ve B−b'den Tv ve Tb. Bunları raporlarınıza ya da AAVSO'nun dönüşüm aracına girin.
