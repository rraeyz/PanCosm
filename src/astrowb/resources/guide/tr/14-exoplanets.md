# Ötegezegenler
**Ötegezegenler** penceresi kaydedilmiş bir ışık eğrisine tam bir geçiş modeli uydurur. Başlangıç sayfasındaki bloğundan ya da Pencere menüsünden açılır. Aşamalar sol rayda sıralanır: Veri, Yıldız, Gezegenler, Model, Uydur, Belirsizlik, Sonuçlar. Ana görünümde uydurulan modelle birlikte geçiş ve artıkları, uydurulan parametrelerin tablosu ve sonucu veren bir metin satırı vardır.

## Veri {#exoplanets-data}
**Işık eğrilerini aç…** bir ya da daha çok ışık eğrisi dosyası alır: Fotometri penceresinin yazdığı `.lc.ecsv` dosyaları ya da zaman, akı ve hata sütunlu bir CSV / metin tablosu (en az 10 satır). Tablo her dosyayı nokta sayısı, gün olarak zaman aralığı ve zaman ölçeğiyle listeler; bir satırı seçmek uydurulacak ışık eğrisini seçer ve varsa son uydurmasını gösterir. Okunamayan dosya, nedeniyle birlikte grafiğin altındaki metinde belirtilir. ExoClock dosyası için zamanların BJD_TDB olması gerekir (bkz. Sonuçlar).

## Yıldız {#exoplanets-star}
Yıldızın kenar kararması **u1** ve **u2** katsayılı ikinci dereceden bir yasayı izler (varsayılan 0,4 ve 0,2). **Kenar kararmasını uydur** işaretlenmedikçe sabittir; tek bir gece bunları nadiren belirler, bu yüzden sabit bırakıp yıldızın sıcaklığına ve süzgece uygun değerleri bir tablodan alın.

## Gezegenler {#exoplanets-planets}
Geçişin başlangıç değerleri: **Periyot (g)** (sabit: tek bir geçiş onu belirlemez), **Geçiş orta zamanı** ve **Rp/R★** (ikisi de varsayılan olarak *auto*: düzleştirilmiş eğrideki çukurun ortası ve derinliğinin karekökü), **a/R★** ve **Çarpma parametresi**. Uydurma, orta geçiş zamanını, Rp/R★, a/R★ ve b'yi bu değerlerden başlayarak iyileştirir. Dönem ve diğerlerinin ilk tahmini Planlama penceresinden (**Efemerisle ekle**) ya da Fotometri penceresinden NASA Exoplanet Archive'dan alınabilir; bu pencere onları aramaz.

## Model {#exoplanets-model}
**Eğilimi gider** geçişle birlikte uydurulan, gezegenden gelmeyen yavaş eğilimlerin niceliklerini listeler: airmass, fwhm, sky, x, y, virgülle ayrılmış (varsayılan `airmass`; boş: yok). Işık eğrisi bu sütunları içermelidir; Fotometri penceresi onları yazar.

## Uydur {#exoplanets-fit}
**Geçişi uydur** seçili ışık eğrisini arka planda uydurur; hazır olunca sonuç grafiğin, tablonun ve metnin yerini alır. Durdur düğmesi durum çubuğundadır.

## Belirsizlik {#exoplanets-uncertainty}
Artıklar zamanda ilişkiliyse en küçük kareler hataları fazla küçük çıkabilir. **Kırmızı gürültüyü hesaba kat (hatalar × β)** hataları β ile çarpar; β, artıkların saçılımının zaman kutusuyla beklendiği kadar azalmamasının çarpanıdır. **MCMC adımları** uydurmadan sonra bir sonsal örnekleme çalıştırır (yakınsayınca erken durur; 0: yok) ve orta geçiş zamanı, Rp/R★, a/R★ ve b için asimetrik hatalar verir; metin *not converged* diyorsa daha çok adım kullanın.

## Sonuçlar {#exoplanets-results}
Metin ve tablo orta geçiş zamanını (BJD), derinliği (ppt ve mmag), T14 ve T23 sürelerini, a/R★, b, eğimi, yıldız yoğunluğunu, indirgenmiş χ²'yi, artıkların RMS'ini ve β'yı verir. **ExoClock dosyası…** ExoClock geçiş zamanlaması projesinin yükleme dosyasını (BJD_TDB zaman, normalleştirilmiş akı, hata), **ETD dosyası…** Exoplanet Transit Database için dosyayı (Jülyen günü, kadir, hata) yazar. Zamanları BJD_TDB olmayan bir ışık eğrisi ExoClock için yazılamaz: ölçerken hedefin konumunu verin.
