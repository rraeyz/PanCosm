# Planlama
**Plan** sayfası hedeflerinizin bu gece ne zaman gözlenebileceğini ve gece boyunca hangi örtme ya da geçişlerin olacağını söyler. Kendi penceresinde açılır (Başlangıç sayfasındaki bloğu ya da Pencere menüsü); kendi menüleri vardır: **Hedefler** (hedef ekle, efemerisiyle ekle, seçileni kaldır) ve **Gece** (geceyi planla, poz süresi, program yap, Gözlem penceresine gönder). Menülerin altındaki simgeler aynı işi yapar; **Görünüm → Araç çubuğu yazıları** adlarını gösterir.

## Gözlem yeriniz
Gözlemevinin **enlemini** (derece, kuzey artı), **boylamını** (derece, doğu artı) ve **yüksekliğini** (metre) girin. Bunlar hatırlanır. Dikine hızların barisentrik düzeltmesinde ve alacakaranlık zamanlarında da kullanılır.

**Gözlem yeri** alanına bilinen bir gözlemevinin adını yazın (örneğin *TUG*, *Roque de los Muchachos*, *Kitt Peak*): yazarken yaklaşık 380 gözlemevinin listesi açılır, birini seçmek enlem, boylam ve yüksekliği doldurur. Liste astropy'den gelir ve internetsiz çalışır.

## Gece ve yükseklik sınırı
- **Gece başlangıcı:** gecenin başladığı akşamın tarihi.
- **En düşük yükseklik (°):** bunun altındaki hedef gözlenemez sayılır (ağaçlar, binalar, kalın hava). 20–30° tipiktir.

## Hedef eklemek
Bir **ad** (SIMBAD'da aranır, ör. `HAT-P-32`, `V523 Cas`, `M 42`) ya da **koordinat** (`02:04:10 +46:41:16` veya ondalık derece) yazıp **Ekle**'ye basın.

**Efemerisle ekle** adı AAVSO **VSX** kataloğunda (değişen yıldızlar) ya da **NASA Ötegezegen Arşivi**'nde (`HAT-P-32 b` gibi gezegenler) arar; koordinat, periyot, başlangıç zamanı ve süreyi doldurur, böylece gecenin örtmeleri ya da geçişleri hemen listelenir. Örten çiftlerde başlangıç zamanı VSX'in birinci minimum zamanıdır (HJD; BJD'den saniyeler kadar farklı) ve *İkincil* işaretlenir; zonklayan yıldızlarda yalnızca periyot gösterilir. İnternet gerekir.

- Bir kez bulunan adlar önbelleğe alınır; sonradan internet olmadan da planlama yapılabilir.
- **Seçileni kaldır** tablodaki satırları siler.

## Örtmeler ve geçişler
Örten çiftler ve ötegezegenler için hedef tablosunun sütunlarını doldurun:

- **T0 (BJD):** bir birinci minimum ya da geçiş ortası zamanı (BJD_TDB).
- Örtmenin ya da geçişin **Periyodu (g)** ve **Süresi (g)**.
- **İkincil:** ikinci minimumları da (evre 0,5) listelemek için işaretleyin.

Plan, gecenin her olayını UTC olarak başlangıç, orta ve bitiş zamanıyla, yükseklik sınırına ve karanlığa göre **gözlenebilir** olup olmadığıyla (*evet*, *kısmen* ya da hiç) listeler.

## Grafiği okumak
**Geceyi planla** her hedefin yüksekliğini bütün gece boyunca UTC zamana karşı çizer; üst eksende yerel saat vardır (**Yerel saat (UTC'den fark, saat)**: *Otomatik*, bu bilgisayarın o tarihteki saat dilimini yaz saatiyle birlikte alır; başka yerdeki bir gözlemevi için farkı yazın, örn. yazın La Palma için 1). Grafiğin yazıları, makaleye ya da rapora olduğu gibi girebilmesi için arayüz dili ne olursa olsun İngilizcedir:

- mavi gölge gün batımından itibaren sivil (−6°), denizcilik (−12°) ve astronomik (−18°) alacakaranlıkla adım adım koyulaşır; en koyu kısım astronomik gecedir;
- kesikli gri eğri **Ay**'dır, aydınlanma yüzdesi açıklamada yazar;
- noktalı kırmızı çizgi en düşük yükseklik sınırınızdır;
- sağ eksen **airmass/hava kütlesini** verir; fotometri için hava kütlesi 2'nin (yükseklik 30°'nin üstü) altı en iyisidir;
- kırmızı üçgenler hedefin eğrisi üzerinde her örtmenin ya da geçişin ortasını gösterir.

Grafiğin altındaki satır astronomik gecenin başlangıç ve bitişini UTC ve yerel saat olarak ve olay sayısını verir; olay tablosu her olayın ortasını yerel saatle de verir. Yazın kutuplara yakın yerlerde **astronomik gece olmayabilir**.

## Plandan gözleme
**Program yap** (*Geceyi planla*'dan sonra) geceyi birden çok hedef için bir programa çevirir: önce gözlenebilir her örtme ya da geçiş, öncesinde ve sonrasında 30 dakikalık taban çizgisiyle (ikisi çakışırsa listenizde üstte olan hedef kazanır); karanlık zamanın geri kalanı birer saatlik bloklarla, her blokta yükseklik sınırınızın en üstünde kalan hedefe. **Gözlem sayfasına gönder** her bloğu başlangıç ve bitişiyle sekansa verir; orada ayarladığınız poz satırları her hedef için kullanılır.

Plandaki zamanları Gözlem sayfasında bir sekansın **Başlangıç** ve **Bitiş**'i olarak kullanın (ya da `dusk` ve `dawn` yazın) veya *Örten çift gecesi* ya da *Ötegezegen geçişi* gibi bir otomasyon şablonundan başlayın.

**Poz süresi…** istenen sinyal/gürültü için ne kadar poz verileceğini CCD denkleminden hesaplar: yıldızın kadirini, sisteminizin sıfır noktasını (saniyede bir elektron veren kadir; parlaklığı bilinen bir yıldızda bir kez ölçün), gökyüzünü, okuma gürültüsünü, karanlık akımı ve açıklığı girin. Yıldızın en parlak pikselinin kaç saniyede doyuma ulaşacağını da söyler, poz fazla uzun olacaksa birkaç kısa kare önerir. Değerler hatırlanır.
