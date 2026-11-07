# Uzaktan algılama
**Uzaktan algılama** sayfası uydu ve hava görüntülerini (Landsat, Sentinel-2, insansız hava aracı) ve her çok bantlı görüntüyü inceler.

## Görüntü açmak
**Görüntü aç…** çok bantlı GeoTIFF (Cloud-Optimised GeoTIFF dahil), FITS, JPEG2000 (ör. Sentinel-2 bant dosyaları), NetCDF (3 ve 4) ya da HDF5 dosyası açar. NetCDF / HDF5'te ana ızgaradaki her 2-B değişken bir banttır, dolgu değerleri boş olur, CF enlem / boylam koordinatları harita konumunu verir (ürünler bu konumla GeoTIFF olarak yazılır). JPEG2000 dosyaları harita konumları olmadan okunur. Düğmenin altındaki satır bant sayısını, boyutu ve harita izdüşümünü verir. **Göster** gösterilecek bandı seçer; bir piksele tıklamak orada bütün bantların değerlerini ve harita koordinatını gösterir. Bir ESA Sentinel-2 ürününün (.SAFE klasörü içindeki) bant dosyaları, ürünün MTD_MSIL2A.xml / MTD_MSIL1C.xml dosyasındaki ofset ve ölçekle yansımaya çevrilir: işleme sürümü 04.00'dan (2022) beri saklanan sayılar +1000 taşır ve bunlar üzerinden hesaplanan NDVI gibi indisler yanlış olur. Element84 / AWS Sentinel-2 COG dosyalarında ofset zaten çıkarılmıştır, oldukları gibi okunur.

## Bant rolleri ve indisler
**Bant rolleri**'nde hangi bandın **BLUE (mavi), GREEN (yeşil), RED (kırmızı), NIR (yakın kızılötesi)** ve **SWIR (kısa dalga kızılötesi)** olduğunu belirtin. Sonra **İndis…** şunları sunar:

- **NDVI** (NIR − RED) / (NIR + RED) — bitki örtüsü;
- **NDWI** (GREEN − NIR) / (GREEN + NIR) — açık su;
- **EVI** — toprak ve atmosfer için düzeltilmiş bitki örtüsü;
- **SAVI** — parlak toprak üzerindeki bitki örtüsü (L = 0,5);
- **NDBI** (SWIR − NIR) / (SWIR + NIR) — yapılaşmış alanlar.

## Bant matematiği
**Göster** listesindeki bant adlarıyla (ör. `B1`, `B2`, …) herhangi bir ifade yazıp **Hesapla**'ya basın, ör. `(B4 - B3) / (B4 + B3)`. İzin verilenler: + − × / ve üs, karşılaştırmalar ve `sqrt`, `log`, `log10`, `exp`, `abs`, `min`, `max`, `where`. İfadeler güvenle ayrıştırılır, asla kod olarak çalıştırılmaz. Sonucun istatistikleri (en küçük, medyan, en büyük, ortalama ± std) gösterilir.

## Sınıflandırma ve temel bileşenler
- **Sınıflandır (k-ortalamalar)** pikselleri bant değerlerine göre verilen sayıda **sınıfa** ayırır (gözetimsiz): su, orman, tarla, yerleşim genellikle iyi ayrılır.
- **Temel bileşenler** ilişkili bantları birkaç yeni banda sıkıştırır; her birinin açıkladığı varyans listelenir.

Her ürün girdinin coğrafi konum bilgisiyle GeoTIFF olarak kaydedilir; QGIS'te doğru yerde açılır.
