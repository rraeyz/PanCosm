# Yörüngeler ve modeller
**Yörünge ve modeller** sayfası ayrık bir örten çiftin ya da geçiş yapan bir gezegenin ışık eğrisine fiziksel bir model fit eder ve bunu tayfsal yörüngeyle birleştirip mutlak boyutları verir. Modeller kendi penceresinde açılır (Başlangıç sayfasındaki bloğu ya da Pencere menüsü); parametreler ve uydurmalar için kendi Düzen → Geri al / İleri al menüsü vardır. Menüleri: **Dosya → Aç…** ışık eğrisini seçer (ya da dosyayı pencereye bırakın), **Dosya → Bir model eğrisiyle karşılaştır…** ve **Dosya → Dışa aktar** (sonuçlar, PHOEBE, WD, ExoClock / ETD); **Fit** (fit, posterior, MCMC, mutlak boyutlar) ve **Görsel yörünge** (ölçümleri yükle, yörüngeyi fit et).

## Model
Keplerci bir yörüngede kenar kararmalı iki küre. Ayrık çiftlere ve geçişlere uyar. Yakın, biçimi bozulmuş ya da temaslı çiftler Roche modeli ister: onun yerine PHOEBE'ye ya da WD'ye aktarın.

## Işık eğrisi fit etmek
1. **Işık eğrisini** seçin (Fotometri sayfasından ya da başka bir kaynaktan CSV; bir zaman sütunu ve göreli akı ya da kadir).
2. **Periyot (gün)** ve **Birincil minimum (BJD)** verin (O-C sayfasından).
3. Başlangıç değerleri: **r1 + r2** (yarıçaplar toplamı, a cinsinden), **k = r2 / r1**, **Yörünge eğimi (°)**, **Yüzey parlaklığı oranı J**, **Üçüncü ışık**, dış merkezlilik terimleri ve her yıldızın kenar kararması **u1, u2**. Fit edilecek parametreleri işaretleyin.
4. **Fit**: sonuç i, r1, r2, ışık oranı L2/L1 ve e'yi hatalarıyla, rms'i ve χ²ᵣ'yi verir. Grafik veriyi, modeli ve artıkları (O−C) evreye karşı gösterir. **Sonuçları dışa aktar (CSV / LaTeX)…** tüm parametreleri (serbestler hatalarıyla, sabitler işaretli, örneklenmişse MCMC değerleri), türetilen ve mutlak büyüklükleri makaleye hazır bir tablo olarak yazar.

## MCMC belirsizlikleri
En küçük kareler fitinin hataları parametrelerin bağımsız olduğunu varsayar; örten çiftlerde ve geçişlerde değildirler (eğim, yarıçaplar ve kenar kararması birbirinin yerini tutar). **MCMC belirsizlikleri**'ni işaretleyin; fitin çevresinde sonsal dağılım, seçtiğiniz **adım** sayısıyla örneklenir (afin değişmez topluluk örnekleyicisi, emcee): her serbest parametre medyan −/+ 16. ve 84. yüzdelikleriyle verilir; **Sonsal dağılım…** köşe grafiğini (histogramlar ve çiftler) gösterir, ilişkiler bir bakışta görünür. 2000 adım için 1000 nokta başına yaklaşık bir dakika sürer; arka planda çalışır ve iptal edilebilir.

## Mutlak boyutlar
Tayf sayfasında çift çizgili bir yörünge (K1, K2) varsa **Tayftaki çift çizgili yörüngeyle mutlak boyutlar**'ı işaretleyin: kütleler M1, M2, yarıçaplar R1, R2 (Güneş birimi), ayrıklık a ve iki yıldızın log g değerleri hata yayılımıyla hesaplanır.

## PHOEBE ve diğer modeller
- **Fit et ve PHOEBE için dışa aktar…** ışık eğrisini (`lc.txt`), varsa dikine hızları (`rv1.txt`, `rv2.txt`) ve fit edilen parametreleri PHOEBE adlarıyla (`start.json`) bir Roche modeline başlangıç olarak yazar.
- **Fit et ve WD için dışa aktar…** gözlemleri Wilson-Devinney programının sütun düzeninde (`lc.dat`: zaman, akı, ağırlık) ve fit edilen değerleri WD adlarıyla `wd_parameters.txt` dosyasına yazar: PERIOD, HJD0, XINCL, E, PERR0 (radyan), EL3 ve çift çizgili yörünge varsa RM (q), yarıçaplardan hesaplanan yüzey potansiyelleri PHSV ve PCSV, VGA ve A. Bunları kullandığınız WD sürümünün girdi dosyasına yazın; sıcaklıklar, albedolar ve çekim kararması sizin ayarınızdır.
- **Fit et ve ExoClock / ETD için dışa aktar…** (geçişler) iki geçiş zamanlama projesinin yükleme dosyalarını yazar — `<ad>_ExoClock.txt` (BJD_TDB, göreli akı, hata) ve `<ad>_ETD.txt` (BJD_TDB, kadir, hata) — ve `<ad>_summary.txt` dosyasına bu geçişin orta zamanı Tc ± hata (verinin yakınındaki çevrim, fit edilen T0 ve periyottan), derinlik, süre T14, Rp/R*, a/R* ve eğikliği yazar. T0 ve periyodu Plan sayfasındaki efemeris sorgusundan girin, T0'ı (ve biçimi) fit edin, sonra yükleyin; gözlem ayrıntıları (gözlemci, filtre, poz) projelerin kendi formlarına girilir. WASP-12 b'nin gerçek bir geçişiyle denendi (TESS 20. sektör, hedef piksel dosyası burada ölçüldü, ±3,6 saatlik tek geçiş): Tc, NASA SPOC ışık eğrisindeki aynı geçişten 47 sn, bütün sektörün efemerisinden 42 ± 70 sn farklı; derinlik %1,59 (SPOC %1,58).
- **Bir model eğrisiyle karşılaştır…** başka yerde hesaplanmış bir eğriyi (iki sütun: evre ya da zaman, ve akı) verinizin üstüne çizer.

## Görsel çift yıldız yörüngesi
**Görsel çift yıldız yörüngesi** sekmesi, çözümlenmiş bir çift yıldızın yedi yörünge öğesini yoldaşın konum ölçümlerine uydurur.
1. Ölçümleri yazın ya da **yükleyin**; her satıra bir tane, WDS sırasıyla: dönem (yıl), konum açısı θ (derece, kuzeyden doğuya), ayrıklık ρ (yay saniyesi) ve isteğe bağlı olarak ρ'nun (″) ve θ'nın (°) hatası. `#` ile başlayan satırlar atlanır. En az 7 ölçüm gerekir (yedi öğe); çok daha fazlası daha iyidir.
2. İsterseniz **en kısa** ve **en uzun dönemi** (yıl) sınırlayın; öntanımlı olarak ölçümlerin kapsadığı sürenin 0,5 ile 10 katı aranır.
3. Kepler'in üçüncü yasasından toplam kütleyi, M1 + M2 = a³ / (ϖ³ P²), almak için **paralaksı** (mas) girin.
4. **Yörüngeyi uydur**: aralıktaki her dönem, her periastron evresi ve 0 ile 0,95 arası dışmerkezlikler doğrusal Thiele–Innes çözümüyle denenir, sonra yedi öğe birlikte iyileştirilir (Levenberg–Marquardt). Tablo P, T, e, a, i, Ω, ω değerlerini uydurmanın kovaryansından gelen 1σ hatalarla (indirgenmiş χ² ile ölçeklenmiş), ayrıklıkların rms'ini ve kütleyi verir. Grafik görünür yörüngeyi (gökyüzündeki gibi doğu solda), ölçümleri ve O−C çizgilerini gösterir.

Dikine hızlar olmadan Ω ve ω birlikte 180° döndürülebilir: program Ω'yı 0 ile 180° arasında verir. Kısa bir dönem aralığının daha uzun gerçek bir dönemi gizlemediğini denetleyin: farklı aralıklar için χ²ᵣ'yi karşılaştırın. Yöntem: Heintz (1978), *Double Stars*; USNO yörünge kataloglarının kuralları (Beşinci Katalog: Hartkopf, Mason & Worley 2001, AJ 122, 3472; Altıncı Katalog ORB6 olarak sürüyor).
