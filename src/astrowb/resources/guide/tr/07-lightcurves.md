# Işık eğrileri ve O-C
**Işık eğrisi ve O-C** sayfasının üç sekmesi vardır: **Periyot arama**, **Frekans analizi** ve **O-C diyagramı**.

## Periyot arama
Fotometri sayfasında ölçülen ışık eğrisi kendiliğinden kullanılır; ya da **CSV yükle (zaman, akı)…**.

- **Lomb–Scargle** — her deneme periyodunda bir sinüs dalgası uydurur ve değişimin en büyük kısmını açıklayanı seçer. Sinüs biçimli değişimler için: zonklayan yıldızlar, dönme ve lekeler.
- **BLS** (kutu en küçük kareler) — her deneme periyodunda kısa, kutu biçimli bir düşüş uydurur. Gezegen geçişleri ve Algol türü örtmeler için.
- **PDM** (evre saçılımı en küçükleme) — biçim varsaymaz: veriyi her deneme periyoduyla katlar ve noktaların en düzgün üst üste bindiği periyodu seçer. Her biçimdeki ışık eğrisi için, örneğin iki minimumlu örten çiftler.
- **ANOVA** (çok harmonikli varyans analizi) — her deneme periyodunda iki harmonikli bir eğri uydurur ve istatistiksel olarak sınar. RR Lyrae ve sefeid gibi sinüs olmayan düzgün biçimler için.

Her yöntemin nasıl çalıştığı, formülleri ve kaynakları: **Yöntemlerin matematiği** (bu kılavuzun son bölümü). Yöntem listesinin üzerine gelince her birinin tek satırlık özeti görünür.

**TESS ve Kepler:** bir yıldız adı (ya da TIC / KIC numarası) yazın, TESS, Kepler ya da K2 seçin ve **İndir**'e basın. Görevin kendi ışık eğrileri (aletsel eğilimleri düzeltilmiş PDCSAP akısı) MAST arşivinden gelir; işaretli noktalar atılır, her sektör ya da çeyrek normalleştirilip birleştirilir, zamanlar BJD_TDB'dir. Ayar klasöründe saklanır; ikinci indirme anında olur. Sonra periyodu aşağıdaki gibi arayın.

**ZTF ve AAVSO:** ZTF'yi (Zwicky Transient Facility ışık eğrileri, IRSA'dan, yıldızın konumuyla bulunur) ya da AAVSO'yu (AAVSO Uluslararası Veritabanındaki gözlemler) seçip **İndir**'e basın. AAVSO, ZTF ya da ASAS-SN Sky Patrol'dan indirilmiş dosyalar **CSV yükle…** ile de açılır. Tek bant tutulur (en çok noktası olan), üst sınırlar ve bayraklı noktalar atılır, kadirler göreli akıya çevrilir ve zamanlar BJD_TDB'ye dönüştürülür; böylece bu veriler TESS'le ya da kendi verinizle birleştirilebilir.

**En kısa** ve **en uzun periyodu** ayarlayın (en uzun, varsayılan olarak zaman aralığının yarısıdır) ve **Ara**'ya basın. Periyodogram ve en iyi periyoda göre katlanmış ışık eğrisi gösterilir. Katlanmış eğriyi kontrol edin: periyodun yarısı ya da iki katı sık görülen bir yanılsamadır, özellikle minimumları eşit örten çiftlerde.

**Evre aralıkları** katlanmış noktaların üstüne ortalama eğriyi çizer. **Işık eğrisini düzenleme:** *Aykırı noktaları at (σ)*, *Zamanda grupla (dk)*, *Tıklayarak nokta sil* (sonra grafikte bir noktaya tıklayın), *Akı ↔ kadir* ve *Düzenlemeleri geri al*. Periyot arama ve frekans analizi düzenlenmiş eğriyi kullanır. *Aykırı noktaları at* her noktayı zamandaki komşularıyla (periyot bulunduktan sonra katlanmış eğrideki komşularıyla da) karşılaştırır; tutulmalar ve zonklamalar silinmez. **Hatalar:** ışık eğrisinde varsa (Fotometri sayfasından, TESS / Kepler / ZTF / AAVSO indirmelerinden ya da CSV dosyasının üçüncü sütunundan), hata çubukları olarak çizilir, her düzenlemeyi izler (aykırı noktalar, gruplama — her ortalamanın hatası —, silinen noktalar, akı ↔ kadir) ve Lomb–Scargle ile BLS aramalarını 1/σ² ile ağırlıklandırır; **Kaydet** onları üçüncü sütun olarak yazar.

## Frekans analizi
Birden çok modlu zonklayan yıldızlar için (δ Scuti, γ Dor, β Cep), Period04 gibi. **En yüksek frekansı** (gün başına çevrim) girin ve **Frekansları analiz et**'e basın:

1. Genlik spektrumu (düzensiz örnekleme için Deeming Fourier dönüşümü) hesaplanır.
2. En yüksek tepe sinüs olarak fit edilir, çıkarılır (**prewhitening**) ve artıklarda yeniden aranır.
3. Her yeni frekans öncekilerle birlikte fit edilir (frekans, genlik, evre hepsi serbest).
4. Sonraki tepenin **S/G**'si (genliği / ±1 c/g içindeki ortalama artık genlik) sınırın altına düşünce durur; Breger ölçütü 4'tür.

Tablo her frekansı, periyodu, genliği ve evreyi hatalarıyla (Montgomery & O'Donoghue 1999) ve S/G ile verir. Grafikler özgün spektrumu, S/G sınırıyla artık spektrumu ve **spektral pencereyi** gösterir: pencerede 1 c/g'de tepe varsa günlük boşluklar her gerçek frekansın ±1 c/g'sinde takma (alias) üretir; bir frekansa inanmadan önce takmasıyla karşılaştırın. **CLEAN uygulanmış spektrumu da göster** işaretlenirse bu takmalar giderilmiş spektrum da çizilir (CLEAN, Roberts, Lehár ve Dreher 1987): gerçek frekans kalır, takmaları düşer.

**Maksimum zamanları** verinin kapsadığı her çevrim için ölçülür (fit edilen eğrinin her maksimumu çevresinde parabol); ışık eğrisi kadir ise *Değerler kadir* kutusunu işaretleyin. **Maksimumları O-C diyagramına gönder** onları O-C listesine ekler.

## O-C diyagramı
O-C (gözlenen eksi hesaplanan), minimum zamanlarının sabit bir periyottan nasıl saptığını gösterir.

1. **Minimum zamanlarını** her satıra bir tane olmak üzere yazın ya da yapıştırın: `zaman [hata] [I/II] [kaynak]` — ör. `2459876.43215 0.00021 I TESS`. Ya da **Dosya yükle…**. Zamanlar BJD ya da HJD olabilir; karıştırmayın.
2. Bir **Referans T0** ve **Periyot (gün)** verin: her minimumun çevrimi bunlardan hesaplanır.
   Ya da **Yıldız** kutusuna yıldızın adını yazıp **Bul**'a basın: T0 ve dönem AAVSO VSX'ten gelir. T0 boş kalırsa ilk birincil minimum kullanılır.
3. **Doğrusal efemeris** ya da **İkinci derece (dönem değişimi)** seçin ve **Fit et ve O-C çiz**'e basın. **Sonuçları dışa aktar (CSV / LaTeX)…** uydurulan değerleri 1σ hatalarıyla, makaledeki gibi yuvarlanmış olarak ve modeli adlandıran bir başlıkla yazar.

Sonuç yeni T0 ve P'yi hatalarıyla verir; ikinci derece fit ayrıca saniye/yıl olarak periyot değişim hızı dP/dt'yi ve indirgenmiş χ²'yi verir. Birincil minimumlar daire, ikinciller kare ile çizilir; alttaki grafik artıkları gösterir.

## Üçüncü cisim ve apsidal hareket
- **Üçüncü cisim (ışık-zaman etkisi):** örten çift üçüncü bir yıldızla ortak kütle merkezi etrafında döner; örtmeler bu yörünge boyunca erken ve geç gelir (Irwin 1952). Fit üçüncü cismin periyodunu P3 (yıl), yarı genliği A (dakika), dış merkezliliği e, ω açısını ve üçüncü yıldızın kütlesi için alt sınır olan kütle fonksiyonunu f(m3) verir. Birden fazla P3'e yayılmış en az 8 minimum gerekir.
- **Apsidal hareket:** dış merkezli yörüngede apsis çizgisi döner; birincil ve ikincil minimumlar zıt yönlerde salınır. İki türü de (I ve II) girin; fit e'yi, 0. çevrimdeki ω'yı, dω/dE'yi (çevrim başına derece) ve apsidal periyodu U (yıl) verir. Model e'de birinci derecedir (e ≲ 0,1 için iyi).
- **MCMC belirsizlikleri:** bu iki modelde kutuyu işaretlerseniz fitten sonra bir Markov zinciri (emcee) çalışır: e ve ω dahil her parametrenin, f(m3) ve U'nun %68 aralığı; parametreler birbirine bağlı olduğunda dürüst hatalar (OCFit'teki gibi). Birkaç saniye sürer; daha çok adım daha kararlı hatalar verir. Doğrusal ve kuadratik efemeris doğrusal problemlerdir; en küçük kareler hataları zaten kesindir, kutu kapalıdır.

## O-C diyagramını okumak
- Eğimli düz bir çizgi: periyot biraz yanlış — fit onu düzeltir.
- Bir parabol: periyot değişiyor (kütle aktarımı, manyetik etkinlik, açısal momentum kaybı).
- Bir dalga: üçüncü bir cismin ışık yolu zaman etkisi ya da apsidal hareket (dış merkezli sistemlerde birincil ve ikincil minimumların zıt yönde kayması).
- Hatalar önemlidir: hatası verilmeyen minimumlar eşit ağırlık alır.
