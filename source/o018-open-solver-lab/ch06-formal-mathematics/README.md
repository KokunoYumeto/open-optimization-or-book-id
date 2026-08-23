# Pendamping terbuka Bab 6: pernyataan matematis formal

Direktori ini menyediakan laboratorium O018 yang terpisah untuk seluruh 12
latihan Bab 6, *Pernyataan Matematis Formal*. Laboratorium memakai aritmetika
rasional eksak, pemeriksaan rank eksak dan NumPy, model Pyomo+HiGHS, serta
sertifikat pembuktian deterministik sesuai jenis soal. Kode tidak mengekstrak
matematika dari prosa pada saat dijalankan dan tidak mereka-reka data yang
tidak diberikan sumber.

## Cakupan

- 12 dari 12 latihan diverifikasi dan tidak ada latihan yang kekurangan data;
- operasi vektor, kombinasi linier, bobot barysentris, perkalian matriks, dan
  himpunan aktif dihitung dengan `fractions.Fraction`;
- rank dihitung ulang dengan eliminasi Gauss eksak dan `numpy.linalg.matrix_rank`;
- lima pemanggilan Pyomo+HiGHS memeriksa LP Latihan 6.5, dua titik pada
  Latihan 6.6, representasi Latihan 6.9, dan LP lempeng Latihan 6.11;
- soal konveksitas dan pembuktian umum memakai sertifikat langsung yang
  memeriksa saksi, identitas afine, linealitas, atau langkah kuantor yang
  dinyatakan sumber;
- lima SVG id-ID yang dapat diakses disediakan hanya untuk geometri yang
  memberi nilai pedagogis: Latihan 6.6, 6.7, 6.8, 6.10, dan 6.11.

Setiap SVG memuat `title`, `desc`, `role="img"`, bahasa `id-ID`, alternatif
teks terstruktur, dan penjelasan jika batas jendela gambar bukan kendala model.
Renderer SVG lokal bersifat deterministik dan tidak memerlukan Matplotlib.

## Menjalankan secara offline

Dari akar lane, gunakan CPython 3.12 dan wheel yang sudah dibekukan:

```powershell
python -m venv <direktori-sementara>
<direktori-sementara>\Scripts\python.exe -m pip install --no-index --find-links=authority/runtime-wheels/windows-cp312-amd64 --require-hashes --only-binary=:all: -r source/o018-open-solver-lab/requirements.lock
<direktori-sementara>\Scripts\python.exe source/o018-open-solver-lab/ch06-formal-mathematics/run_lab.py
<direktori-sementara>\Scripts\python.exe source/o018-open-solver-lab/ch06-formal-mathematics/run_lab.py --check
<direktori-sementara>\Scripts\python.exe -m unittest discover -s source/o018-open-solver-lab/ch06-formal-mathematics -p "test_models.py" -v
<direktori-sementara>\Scripts\python.exe source/o018-open-solver-lab/ch06-formal-mathematics/verify_receipt.py --check
```

`run_lab.py --check` menghitung ulang seluruh hasil dan membandingkan byte
`results.json` serta inventaris SVG tanpa menulis. `verify_receipt.py --check`
menolak receipt jika keluaran tidak sama dengan regenerasi atau jika satu
artifact berubah. Runtime tidak memerlukan jaringan, perangkat lunak kantor,
atau pemecah berpemilik.

Prosa, data adaptasi, hasil yang diharapkan, dan SVG mengikuti CC BY-SA 4.0.
Kode Python baru mengikuti Lisensi MIT di `LICENSE-CODE.txt`; pemisahan hak,
provenance, dan pemberitahuan runtime dijelaskan dalam `ATTRIBUTION.md`.
