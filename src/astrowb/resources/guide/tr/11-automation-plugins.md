# Otomasyon ve eklentiler
**Otomasyon** adımları kendi iş akışınızda zincirler — "klasördeki kareleri kalibre et → ışık eğrisini ölç → minimum zamanını bul → O-C" — ve tek seferde çalıştırır. **Eklentiler** kendi adımlarınızı ekler.

## Hazır şablonlar
**Otomasyon** sayfası hazır şablonları ("şablon" diye işaretli) ve kendi otomasyonlarınızı listeler:

- **Örten çift gecesi** — akşam karanlığından şafağa bir sekans, sonra kalibrasyon, karşılaştırma yıldızları, ışık eğrisi, minimum zamanı (Kwee–van Woerden) ve O-C.
- **Ötegezegen geçişi** — aynısı, geçiş ortası için yamuk fitiyle.
- **Gece sonu kalibrasyonu ve yığma** — şafakta dark ve bias, sonra master'lar, kalibrasyon ve yığılmış bir görüntü.
- **Tayf gecesi → RV → yörünge** — her uzun yarık karesi arkla indirgenir, bir şablona göre dikine hızlar ölçülür ve tek çizgili yörünge fit edilir.
- **Değişen yıldız: ışık eğrisi → periyot** — ışık eğrisi ve Lomb–Scargle periyot araması.

Açıklamasını ve adımlarını görmek için birini seçin.

## Bir otomasyonu çalıştırmak
1. Sağdaki **Girdiler**'i doldurun (klasör ve dosyaların **…** düğmesi vardır). Yalnızca hiçbir adımın üretemediği şeyler sorulur: ör. ham kare klasörü ve hedefin konumu.
2. **Çalıştır**'a basın. Her adım Görevler panelinde normal bir görev olarak çalışır ve projeye kaydedilir; bir sonraki, öncekinin bitmesiyle başlar. Düğmenin altındaki satır hangi adımın çalıştığını söyler.
3. Bitince son adımın sonuçları (ör. minimum zamanı ve O-C) altta gösterilir. Bir adım başarısız olursa otomasyon orada durur ve hata gösterilir.

## Gözlem kısmı
Gözlem sekansı olan şablonlarda **Gözlem sayfasına** vardır: hedefi, başlangıç ve bitişi (ör. dusk ve dawn) ve poz satırlarını doldurur. Koordinatları ekleyin, poz sürelerini kontrol edin ve oradan başlatın. Göndermeden önce **Sekanstan sonra işle**'ı işaretlerseniz, sekans bitince (hava yüzünden erken dursa da, kare çekildiyse) otomasyon sekansın klasöründe kendiliğinden çalışır. Gözlemevi uzaktaysa kareler önce bu bilgisayara kopyalanır, sonra işlenir.

## Kendi otomasyonunuzu kurmak
1. **Yeni** boş bir otomasyon başlatır (ya da bir şablondan başlayıp değiştirin).
2. **Adımlar, sırayla**'nın altındaki listeden bir adım seçip **Adım ekle**'ye basın. **Kaldır**, **Yukarı** ve **Aşağı** sırayı değiştirir.
3. Bir adımı seçince **ayarları** görünür:
   - **←** ile başlayan satırlar girdileridir. Bir girdi varsayılan olarak önceki bir adımın ürettiği (ya da Girdiler'e yazılan) aynı adlı veriyi alır. Bağlamak için başka bir ad yazın, ör. yığma adımının `images` ← `calibrated`;
   - `ad.alan` bir sonucun tek bir alanını ya da her satırın o alanını alır: ör. yörüngenin `time` ← `rvs.bjd`;
   - süslü parantezli metin dosya adı kurar, ör. `{output_dir}/{item}_1d.fits`;
   - diğer satırlar adımın parametreleridir; sayı, `true`/`false`, `null`, `[1, 2]` gibi liste ya da metin yazın.
4. **Farklı kaydet…** onu bir adla ayar klasörünüzde (`automations`) saklar; listede bir dahaki sefere görünür.

Otomasyonlar düz JSON dosyalarıdır; paylaşılabilir: dosyayı başka bir kullanıcının `automations` klasörüne kopyalayın.

## Eklentiler
**Nedir:** eklenti, uygulamaya kendinizin eklediği küçük bir araçtır — uygulamada olmayan bir hesap ya da yalnızca grubunuzun ihtiyaç duyduğu bir iş için. Tek bir Python dosyasıdır. Eklentiler klasörüne konunca **Eklentiler** menüsünde görünür, girdileri için küçük bir form açar, yerleşik her adım gibi çalışır (arka planda, ilerleme ve İptal ile, projeye kaydedilerek) ve bir otomasyonun adımı olarak da kullanılabilir.

**Denemek için programlama bilmeniz gerekmez.** **Eklentiler → Örnek eklentileri kur** hazır üç eklenti ekler:
- **plugin.exposure_time** — istenen sinyal/gürültü için kaç saniye poz verileceği; yıldızın kadiri, sisteminizin sıfır noktası, gökyüzü, okuma gürültüsü ve açıklıktan (CCD denklemi). Yalnızca sayılar, dosya gerekmez.
- **plugin.sky_level** — bir FITS görüntüsünde gökyüzü düzeyi ve gürültüsü (geceleri karşılaştırmak ya da flatları denetlemek için).
- **plugin.light_curve_summary** — bir ışık eğrisi CSV dosyasının nokta sayısı, zaman aralığı, milikadir olarak saçılması ve en derin noktası.

**Eklentiler** menüsünden birini seçin, formu doldurun, Tamam'a basın; sonuç hazır olunca bir pencerede açılır. Hatası olan bir eklenti nedeniyle birlikte "Yüklenemedi" diye listelenir; uygulamayı asla durdurmaz. Eklentiler, kurduğunuz her program gibi sizin yetkilerinizle çalışır: yalnızca güvendiğiniz dosyaları kullanın.

## Kendi eklentinizi yazmak
**Eklentiler → Eklenti klasörünü aç** ile klasörü açın, örneklerden birini kopyalayın, adını değiştirip düzenleyin. Gökyüzü örneğinin tamamı şudur:

```python
from astrowb.engine.steps import step


@step("plugin.sky_level", inputs=("image",), outputs=("sky",), sigma=3.0)
def sky_level(inputs, params, ctx):
    """Median sky level and noise of a FITS image (stars clipped)."""
    from astropy.io import fits
    from astropy.stats import sigma_clipped_stats

    data = fits.getdata(inputs["image"])
    _, median, std = sigma_clipped_stats(data, sigma=params["sigma"])
    return {"sky": {"median": float(median), "noise": float(std)}}
```

- `@step`'ten sonra tırnak içindeki yazı aracın adıdır; `plugin.` ile başlamalıdır.
- `inputs` formun sorduklarıdır (dosya yolları ya da sayılar); onlardan sonraki sözcükler (`sigma=3.0`) varsayılan değerleriyle ayarlardır.
- İşlev bunları `inputs["image"]` ve `params["sigma"]` olarak alır ve sonuçları bir sözlük olarak döndürür (sayılar, yazılar, listeler).
- Uzun işlerde arada `ctx.progress(0.5, "mesaj")`, döngülerin içinde `ctx.check()` çağırın ki İptal çalışsın.
- numpy, scipy, astropy, photutils ve matplotlib her zaman vardır. Dosyayı kaydedin; Eklentiler menüsü bir sonraki açılışında onu bulur.
