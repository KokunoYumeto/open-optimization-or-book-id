# Pendamping terbuka Bab 10: analisis sensitivitas

Direktori ini menyediakan laboratorium O018 yang terpisah untuk seluruh 12
latihan Bab 10, *Analisis Sensitivitas*. Laboratorium mempertahankan matematika
edisi Bahasa Indonesia R017, termasuk tiga koreksi target yang dinyatakan
secara terbuka, lalu memberi sertifikat rasional eksak, perhitungan matriks,
dan pemeriksaan independen dengan Pyomo+HiGHS.

## Cakupan

- 12 dari 12 latihan dicakup dengan ID stabil `10.1` sampai `10.12`;
- 11 latihan memiliki sertifikat komputasional atau pembuktian lengkap;
- Latihan 10.7 diverifikasi secara *fail closed*: aritmetika laporan dapat
  diperiksa, tetapi matriks koefisien kendalanya tidak diberikan sehingga
  laboratorium tidak mereka-reka sebuah PL asal;
- invers basis, solusi basis, harga dual, biaya tereduksi, rentang ruas kanan,
  dan rentang biaya dihitung dengan `fractions.Fraction`;
- 29 pemanggilan Pyomo+HiGHS memeriksa optimum dasar, titik ujung rentang,
  titik tepat di luar rentang, degenerasi, dan kegagalan ekstrapolasi harga
  bayangan;
- tiga SVG id-ID yang dapat diakses memvisualkan rentang biaya Latihan 10.3,
  tekukan degenerat Latihan 10.11, dan nilai linier-sepotong Latihan 10.12.

`expected-results.json` merupakan oracle independen yang ditulis terpisah dari
mesin. `results.json` menyimpan sertifikat eksak, seluruh pemeriksaan solver,
status latihan yang kekurangan data, referensi koreksi, dan inventaris visual.

## Menjalankan secara offline

Dari akar lane, gunakan runtime CPython 3.12 yang dikunci:

```powershell
<python-terkunci> source/o018-open-solver-lab/ch10-sensitivity-analysis/run_lab.py
<python-terkunci> source/o018-open-solver-lab/ch10-sensitivity-analysis/run_lab.py --check
<python-terkunci> -m unittest discover -s source/o018-open-solver-lab/ch10-sensitivity-analysis -p "test_models.py" -v
<python-terkunci> source/o018-open-solver-lab/ch10-sensitivity-analysis/verify_receipt.py --check
```

Runtime lengkap dibekukan dalam `../requirements.lock` dan
`../runtime-receipt.json`. Laboratorium tidak memerlukan jaringan, Microsoft
Excel, Gurobi, CPLEX, atau pemecah berpemilik lain.

Prosa, data adaptasi, oracle, dan SVG mengikuti CC BY-SA 4.0. Kode Python baru
mengikuti Lisensi MIT dalam `LICENSE-CODE.txt`; batas hak, provenance, dan
koreksi dijelaskan dalam `ATTRIBUTION.md`.

