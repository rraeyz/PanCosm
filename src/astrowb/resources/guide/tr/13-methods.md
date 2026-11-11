# Yöntemlerin matematiği
Programdaki her fit ve arama yayımlanmış bir yöntemdir: aşağıdaki model kodun hesapladığı şeydir, adı geçen makale de yöntemin kaynağıdır. Hiçbiri program için uydurulmuş bir pratik kural değildir. Simgeler: t zaman, y ölçülen değer (akı, kadir, hız), σ hatası, N nokta sayısı.

## En küçük kareler, hatalar ve MCMC {#methods-least-squares-errors-mcmc}
Her fit, parametreler p üzerinden ağırlıklı kareler toplamını en küçük yapar:

    χ² = Σ [(yᵢ − model(tᵢ; p)) / σᵢ]²

Doğrusal problemler (efemeris, polinomlar, Thiele–Innes sabitleri, ışık oranları) tam çözülür; diğerleri Levenberg–Marquardt ile (scipy least_squares). 1σ hatalar, kovaryansın (JᵀWJ)⁻¹ köşegeninin karekökleridir (J modelin türevleri, W = 1/σ²). İndirgenmiş χ²ᵣ = χ² / (N − parametre sayısı) 1'den büyükse saçılım hataların söylediğinden büyüktür ve kovaryans χ²ᵣ ile çarpılır. Hata verilmemişse artıkların saçılımı hata olarak alınır.

**MCMC** ("MCMC belirsizlikleri" kutuları): afin-değişmez topluluk örnekleyicisi (Goodman & Weare 2010; emcee, Foreman-Mackey ve ark. 2013) parametre takımlarını exp(−χ²/2) ile orantılı olasılıkla çeker (fiziksel sınırlar içinde düz önseller); en küçük kareler çözümünün çevresinden başlar. Zincirin ilk yarısı atılır; her parametre ortanca ve 16. ile 84. yüzdelikleriyle verilir. Kovaryanstan farklı olarak, parametreler birbirine bağlı olduğunda da (eğim ve yarıçaplar, e ve ω) doğrudur.

## Periyot arama {#methods-period-search}
Dört yöntemin hepsi bir frekans ızgarası (f = 1/P) dener; adımı son noktanın evresini sabit küçük bir miktar kaydırır, böylece hiçbir tepe iki deneme periyodu arasına düşemez. En iyi tepe sonra 50 kat sık bir ızgarada inceltilir.

**Lomb–Scargle** (Lomb 1976, Ap&SS 39, 447; Scargle 1982, ApJ 263, 835; kayan ortalama ve hatalarla Zechmeister & Kürster 2009, A&A 496, 577). Her f'de bir sinüs dalgası artı sabit en küçük karelerle uydurulur:

    y(t) = c + a cos 2πft + b sin 2πft,     güç P(f) = 1 − χ²(f) / χ²₀

χ²₀ yalnız sabite aittir. P, sinüsün açıkladığı varyans payıdır (0 ile 1 arası). Sinüs benzeri eğriler için en iyisidir: zonklamalar, lekeler, elipsoidal değişim.

**BLS — kutu en küçük kareler** (Kovács, Zucker & Mazeh 2002, A&A 391, 369; astropy). Her f'de, her deneme süresi q ve evre için katlanmış eğriye bir kutu uydurulur: dışarıda H düzeyi, içeride H − δ. Derinlik ağırlıklı ortalamaların farkıdır, δ = ȳ_dış − ȳ_iç; güç log-olabilirlikteki iyileşmedir, ½ δ² / σ_δ². Kısa, düz tabanlı düşüşler için en iyisidir: geçişler, Algol türü örtmeler.

**PDM — evre saçılımı en küçükleme** (Stellingwerf 1978, ApJ 224, 953). Veri deneme periyoduyla katlanır ve M evre kutusuna bölünür (varsayılan 20). s² kutuların içindeki birleşik varyans, σ² toplam varyans olmak üzere:

    s² = Σⱼ (nⱼ − 1) sⱼ² / (Σⱼ nⱼ − M),     θ = s² / σ²

Doğru periyotta bir kutunun noktaları üst üste biner ve θ küçüktür; grafik 1 − θ'yı gösterir. Biçim varsayılmaz, bu yüzden iki minimumlu örten çiftlere uyar.

**ANOVA — çok harmonikli varyans analizi** (Schwarzenberg-Czerny 1996, ApJ 460, L107). Her f'de n = 2 harmonikli bir Fourier serisi uydurulur,

    y(t) = c + Σₖ₌₁ⁿ [aₖ cos 2πkft + bₖ sin 2πkft]

ve açıkladığı varyans, varyans analizinin F istatistiğiyle artık varyansla karşılaştırılır:

    Θ = [(N − 2n − 1) / 2n] · P / (1 − P)

(P açıklanan pay, Lomb–Scargle'daki gibi). İki harmonik sinüs olmayan biçimleri izler (RR Lyrae, sefeidler, çiftler) ve F istatistiğinin dağılımı bilinir; böylece farklı eğrilerin tepeleri karşılaştırılabilir.

**Örtüşmeler (alias).** Örnekleme (geceler, uydu yörüngeleri) tekrarlanır; her gerçek f frekansı f ± 1/T_boşluk'ta da tepe verir. Minimumları eşit örten çiftlerde en güçlü tepe çoğu zaman gerçek periyodun yarısındadır: katlanmış eğriye bakın.

## Frekans analizi ve önbeyazlatma {#methods-frequency-analysis-prewhitening}
Düzensiz örneklenmiş verinin genlik tayfı (Deeming 1975, Ap&SS 36, 137):

    A(f) = (2/N) | Σ (yᵢ − ȳ) exp(−2πi f tᵢ) |

**Tayfsal pencere** aynı toplamdır, yᵢ − ȳ yerine 1 konur; yan tepeleri örneklemenin örtüşmeleridir. En yüksek tepe en küçük karelerle uydurulur, sonra o ana kadar bulunan bütün frekanslar birlikte, her biri kendi genliği ve evresiyle:

    y(t) = c + Σₖ Aₖ sin 2π(fₖ t + φₖ)

Uydurulan eğri çıkarılır (**önbeyazlatma**) ve artıklar yeniden aranır. Bir frekans S/N = Aₖ / (±1 c/d içindeki ortalama artık genlik) ≥ 4 oldukça tutulur (Breger ve ark. 1993, A&A 271, 482). Hatalar (Montgomery & O'Donoghue 1999, DSSN 13, 28), σ artıkların rms'i ve T zaman aralığı olmak üzere:

    σ(f) = √6 σ / (π √N A T),    σ(A) = √(2/N) σ,    σ(φ) = σ(A) / (2π A)  (çevrim cinsinden)

**CLEAN** (Roberts, Lehár & Dreher 1987, AJ 93, 968) pencerenin yan loblarını tayftan çıkarır: her seferinde en yüksek tepenin bir kesri (0,2).

## Minimum zamanları {#methods-times-minimum}
**Kwee & van Woerden** (1956, BAN 12, 327). Işık eğrisi düzgün bir ızgaraya aradeğerlenir ve bir deneme zamanı T'ye göre yansıtılır. İnen ve çıkan kol arasındaki ortalama kare fark S(T), minimum zamanında en küçüktür. Yakınında S bir paraboldür, S(T) = aT² + bT + c, dolayısıyla

    T_min = −b / 2a,     σ² = (4ac − b²) / (4a² (Z − 1))

Z bağımsız nokta çiftlerinin sayısıdır. Klasik formül gürültülü veride hatayı küçük verir (Deeg 2020, Galaxies 9, 1); bu yüzden bir bootstrap hatası da (simetrik fitin artıkları 200 kez yeniden örneklenir) hesaplanır ve büyük olanı bildirilir.

**Polinom**: minimum çevresindeki noktalara en küçük karelerle bir parabol; T_min tepe noktasında, hata kovaryanstan.

**Yamuk** (düz tabanlı geçişler için): derinliği δ, toplam süresi T₁₄ ve giriş süresi τ olan, T_min'de ortalanmış simetrik bir yamuk, doğrusal bir taban üzerinde; altı parametre en küçük karelerle uydurulur.

## Efemeris ve O-C {#methods-ephemeris-o-c}
Minimumlar E = round((T − T₀) / P) devir numarasıyla numaralanır ve şu modelle uydurulur:

    doğrusal:   T(E) = T₀ + P E
    ikinci derece: T(E) = T₀ + P E + Q E²,     dP/dt = 2Q / P

Her minimum 1/σ² ile ağırlıklandırılır. Fit ortadaki devir çevresinde yapılır (T₀ ile P'nin en az bağımlı olduğu yer) ve verdiğiniz devre geri taşınır. O − C = T_gözlenen − T₀ − P E. dP/dt saniye/yıl olarak gösterilir.

## Üçüncü cisim ve aps hareketi {#methods-third-body-apsidal-motion}
**Işık-zaman etkisi** (Irwin 1952, ApJ 116, 211). Örten çift üçüncü bir yıldızla kütle merkezi çevresinde döner; ışık şu kadar erken ya da geç gelir:

    τ = A [ (1 − e²) / (1 + e cos ν) · sin(ν + ω) + e sin ω ],     A = a₁₂ sin i / c

ν, üçüncü cisim yörüngesinin (periyot P₃, periastron T₃) gerçek ayrıklığıdır; Kepler denklemi M = E − e sin E'den bulunur. T = T₀ + P E + τ modeli uydurulur; kütle fonksiyonu buradan çıkar: f(m₃) = (a₁₂ sin i)³ / P₃² (AU, yıl, güneş kütlesi).

**Aps hareketi** (Giménez & García-Pelayo 1983, Ap&SS 92, 203; e'de birinci derece, i ≈ 90°). ω = ω₀ + ω̇ E ve anomalistik periyot Pₐ = Pₛ / (1 − ω̇/360°) ile:

    T_I  = T₀ + Pₛ E − (Pₐ/π) e cos ω
    T_II = T₀ + Pₛ E + Pₐ/2 + (Pₐ/π) e cos ω

Birincil ve ikincil minimumlar ters yönlerde salınır; aps periyodu U = 360° / ω̇ devirdir. e yaklaşık 0,1'in üstündeyse yüksek dereceli terimler önem kazanır.

## Örten çift ışık eğrisi {#methods-eclipsing-binary-light-curve}
Kepler yörüngesinde iki küre (EBOP / JKTEBOP'un küresel yaklaşımı, Popper & Etzel 1981, AJ 86, 102; Southworth 2013, A&A 557, A119). Yarıçaplar r₁, r₂ büyük yarı eksen biriminde olmak üzere izdüşüm uzaklığı:

    d = (1 − e²) / (1 + e cos ν) · √(1 − sin² i sin²(ν + ω))

Her yıldızın ikinci dereceden kenar kararması vardır, I(μ) = I₀ [1 − u₁(1 − μ) − u₂(1 − μ)²]; J = I₀,₂ / I₀,₁ yüzey parlaklığı oranıdır. Bir disk ötekini örttüğünde kaybolan ışık, I'nın örtülen kısım üzerindeki integralidir; Gauss–Legendre kareleme ile hesaplanır:

    ΔF = ∫ I(x) · 2x θ(x) dx,     θ(x) = arccos[(x² + d² − r_öndeki²) / (2xd)]

Model akısı F = (1 − L₃)(F₁ + F₂ − ΔF)/(F₁ + F₂) + L₃ (örtme dışında 1; üçüncü ışık L₃ toplamın bir kesri) en küçük karelerle uydurulur (istenirse MCMC ile). Yansıma, gelgit bozulması ve kütle çekim kararması modellenmez; yakın çiftler için PHOEBE ya da WD gerekir (dışa aktarma düğmeleri).

## Dikine hızlar ve tayfsal yörüngeler {#methods-radial-velocities-spectroscopic-orbits}
**Çapraz ilişki** (Tonry & Davis 1979, AJ 84, 1511). Tayf ve şablon bir ln λ ızgarasındadır; orada hız bir kaymadır: Δln λ = v/c. Normalleştirilmiş ilişki C(v) hızda tepe yapar; en yüksek üç noktadan geçen parabol hızı verir; hata Zucker'a (2003, MNRAS 342, 1291) göre:

    σᵥ² = −[N · C''/C · C² / (1 − C²)]⁻¹

**TODCOR** (Zucker & Mazeh 1994, ApJ 420, 806) iki şablonla iki kaymada aynı anda ilişki kurar:

    R(s₁, s₂) = [C₁(s₁) + α C₂(s₂)] / √(1 + 2α C₁₂(s₁ − s₂) + α²)

α (ışık oranı) her noktada çözülür. En yüksek R iki hızı birden verir.

**Genişleme fonksiyonu** (Rucinski 1992, AJ 104, 1968; 2002, AJ 124, 1746). Gözlenen tayf, şablonun B(v) ile evrişimidir: P = D · B doğrusal sistemi, en küçük karelerle (tekil değer ayrışımı) çözülür. Her yıldız kendi hızı, v sin i'si ve ışık payıyla bir dönme profili olarak görünür (Gray 2005, denk. 18.14).

**Yörünge** (tek ve çift çizgili):

    v(t) = γ + K [cos(ν + ω) + e cos ω],     M = 2π(t − T)/P = E − e sin E

parametre olarak √e cos ω ve √e sin ω ile en küçük karelerle uydurulur (dairesel yörüngeye yakın kararlı); çift çizgili çiftte iki yıldız P, T, e, γ'yı paylaşır ve ω₂ = ω₁ + 180°. Türetilen büyüklükler (Hilditch 2001, denk. 2.52–2.53):

    f(m) = P K³ (1 − e²)^{3/2} / 2πG,     m₁ sin³ i = P (K₁ + K₂)² K₂ (1 − e²)^{3/2} / 2πG
    a sin i = P (K₁ + K₂) √(1 − e²) / 2π

Işık eğrisinin eğimi ve yarıçaplarıyla: kütleler, yarıçaplar R = r · a ve log g, her girdinin aynı rastgele çekilişlerinden (JKTABSDIM'in yaptığı gibi); böylece hatalar bağımlılıklarıyla birlikte yayılır.

## Görsel çift yörüngesi {#methods-visual-binary-orbit}
Thiele–Innes biçimi (Heintz 1978, Double Stars). Kepler denkleminden dış merkez ayrıklığı E ile:

    X = cos E − e,    Y = √(1 − e²) sin E
    x = ρ cos θ = A X + F Y,    y = ρ sin θ = B X + G Y

Sabit P, T ve e için A, B, F, G sabitleri doğrusaldır: tam çözülür. P, T, e bir ızgarada aranır, sonra yedi öğenin hepsi Levenberg–Marquardt ile birlikte inceltilir. Campbell öğeleri a, i, Ω, ω, A, B, F, G'den çıkar; toplam kütle Kepler'in üçüncü yasasından: M₁ + M₂ = a³ / (ϖ³ P²) (a ve paralaks ϖ yay saniyesi, P yıl).

## Tayflar: dalga boyu, atmosfer, tellürik, ayrıştırma {#methods-spectra-wavelength-atmosphere-telluric}
**Dalga boyu çözümü**: ark çizgileri Gauss fitiyle ortalanır; λ(x) = Σ cₖ xᵏ sigma kırpmayla uydurulur, IRAF identify'ın yaptığı gibi. Eşel tayflarda ızgara denklemi m·λ'yı piksel x ve mertebe (order) m'nin düzgün bir fonksiyonu yapar; tek bir yüzey Σ cᵢⱼ xⁱ mʲ bütün mertebeleri kapsar (IRAF ecidentify; Baranne ve ark. 1996).

**Atmosfer parametreleri** (iSpec / SME yaklaşımı, önceden hesaplanmış bir ızgarada): gözlenen tayf şöyle modellenir:

    F(λ) = Pₖ(λ) · [S(Teff, log g, [Fe/H]) ∗ G_dön(v sin i) ∗ G_alet(R)](λ / (1 + v/c))

S, PHOENIX ızgarasında aradeğerlenir (Husser ve ark. 2013); Pₖ her dalga boyu parçasında aletin tepkisini üstlenen düşük dereceli bir polinomdur; Levenberg–Marquardt ile uydurulur.

**Tellürik düzeltme**: soğurma optik derinlik gibi ölçeklenir, T_bilim = T_std^s, s ≈ hava kütlesi oranı; s = Σ ln F ln T / Σ (ln T)² tellürik bantların içinde; piksel altı bir kayma da uydurulur.

**Ayrıştırma (disentangling)** (González & Levato 2006, A&A 448, 283): her yıldızın tayfı, öteki yıldızın o anki tayfı çıkarıldıktan sonra kendi durgun çerçevesine kaydırılmış gözlenen tayfların ortalamasıdır; yakınsayana kadar tekrarlanır.

## Fotometri {#methods-photometry}
**Açıklık fotometrisi**: gökyüzü bir halkanın sigma kırpılmış düzeyidir; F = açıklıktaki toplam − N_açk · gök; hatası, gökyüzü gürültüsü σ_gök halkada ölçülen CCD denklemidir (Merline & Howell 1995, Exp. Astron. 6, 163):

    σ_F² = F / kazanç + N_açk (1 + N_açk / N_gök) σ_gök²

**Sönümleme**: mᵢⱼ = cⱼ + k Xᵢ (her karşılaştırma yıldızı için bir sabit, tek k), Bouguer doğrusu.

**Dönüşüm** (iki filtre A, B için AAVSO kuralı): (A − B) = T_ab (a − b) + Z_ab, (B − b) = T_b (A − B) + Z_b; a, b aletsel kadirler; standart bir alanda en küçük karelerle uydurulur.
