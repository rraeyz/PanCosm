# Overview
Observations were done at Tartu Observatory, Estonia in 2024-06-21, using a Shelyak Whoppsel fibre-fed moderate-resolution echelle spectrograph named TOFES (Tartu Observatory Fibre-fed Echelle Spectrograph) attached to a 20 cm F/5 Newtonian-type amateur telescope.

Observations were carried out using a 50 micrometre fibre between the telescope and the spectrograph,
providing spectral resolution R~32000.

# Datasets
The collection contains four datasets: for Sun, CN Boo, Vega, and Arcturus together with their
corresponding calibration files. Thorium-Argon hollow cathode lamp comparison spectra were taken
close in time to target spectra. FITS files contain rich set of metadata which is useful for pre-processing and reduction of the data.

## Solar dataset
- Sun_Object_20s*.fit -- spectra of Sun taken are spectra of sky before sunset
- Sun_Calibration_35s*.fit -- ThAr spectra taken immediately after solar spectra
- Bias_0s_20240621_191216*.fit -- corresponding Zero / Bias frames
- Flat_5s_20240621_192503*.fit -- corresponding tungsten + LED flats
- Dark_20s_20240621_191508*.fit -- corresponding dark frames

## Vega dataset
- Vega_Object_25s*.fit -- spectra of Vega
- Vega_Calibration_30s*.fit -- ThAr spectra taken immediately after Vega spectra
- Flat_5s_20240621_232635*.fit -- tungsten + LED flats for Vega dataset
- Dark_5s_20240621_232331*.fit -- dark frames for Vega dataset
- Bias_0s_20240621_232157*.fit -- Zero / Bias frames for Vega dataset

## CN Boo dataset
- Arcturus_Object_300s_20240621_214724*.fit -- spectra or CN Boo
- Bias_0s_20240621_221716*.fit -- Zero / Bias frames for CN Boo
- Dark_60s_20240621_221843*.fit -- dark frames for CN Boo dataset
- Flat_5s_20240621_222912*.fit -- tungsten + LED flats for CN Boo dataset
- Arcturus_Calibration_30s_20240621_222456*.fit -- ThAr spectra taken after CN Boo spectra

## Arcturus dataset
- Arcturus_Object_5s_20240621_230805*.fit -- spectra of Arcturus
- Bias_0s_20240621_221716*.fit -- Zero / Bias frames for Arcturus
- Dark_60s_20240621_221843*.fit -- dark frames for Arcturus dataset
- Flat_5s_20240621_222912*.fit -- tungsten + LED flats for Arcturus dataset
- Arcturus_Calibration_30s_20240621_222456*.fit -- ThAr spectra taken before Arcturus spectra


# Notes
*.srl files are XML-files from data acquisition and spectrograph control software Demetra, which
describe collected datasets as baskets with Name values as Object, Bias, Dark, Flat, and Calibration.
