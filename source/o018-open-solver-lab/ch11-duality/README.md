# Pendamping terbuka Bab 11: dualitas dan kelonggaran komplementer

Direktori ini menyediakan laboratorium O018 yang terpisah untuk seluruh 17
latihan Bab 11, *Dualitas*. Laboratorium mempertahankan matematika edisi Bahasa
Indonesia R017, termasuk tiga koreksi sumber yang sudah dinyatakan secara
terbuka, lalu memberi sertifikat eksplisit dan pemeriksaan independen dengan
Pyomo+HiGHS.

## Cakupan

- 17 dari 17 latihan dicakup dengan ID stabil `11.1` sampai `11.17`;
- latihan konseptual dan pembuktian memiliki rekaman verifikasi eksplisit,
  bukan jawaban kosong atau model yang direka;
- pasangan primal--dual representatif memeriksa dualitas lemah dan kuat,
  bentuk campuran, harga bayangan, dan kelonggaran komplementer;
- klasifikasi `optimal`, `infeasible`, dan `unbounded` diperiksa langsung;
- sertifikat aljabar menjelaskan dua masalah yang sama-sama taklayak serta
  contoh terkoreksi dengan primal taklayak dan dual takterbatas;
- satu SVG id-ID yang dapat diakses memvisualkan daerah layak dual Latihan
  11.16 dan titik optimum harga sumber dayanya.

`expected-results.json` merupakan oracle independen yang ditulis terpisah dari
mesin. `results.json` menyimpan sertifikat, seluruh pemeriksaan solver, status
setiap latihan, referensi koreksi, cacat hulu berkeyakinan tinggi, dan
inventaris visual.

## Menjalankan secara offline

Dari akar lane, gunakan runtime CPython 3.12 yang dikunci dan nonaktifkan
penulisan bytecode:

```powershell
$env:PYTHONDONTWRITEBYTECODE = "1"
<python-terkunci> source/o018-open-solver-lab/ch11-duality/run_lab.py
<python-terkunci> source/o018-open-solver-lab/ch11-duality/run_lab.py --check
<python-terkunci> -m unittest discover -s source/o018-open-solver-lab/ch11-duality -p "test_models.py" -v
<python-terkunci> source/o018-open-solver-lab/ch11-duality/verify_receipt.py --check
```

Runtime lengkap dibekukan dalam `../requirements.lock` dan
`../runtime-receipt.json`. Laboratorium tidak memerlukan jaringan, Microsoft
Excel, Gurobi, CPLEX, atau pemecah berpemilik lain.

Prosa, data adaptasi, oracle, dan SVG mengikuti CC BY-SA 4.0. Kode Python baru
mengikuti Lisensi MIT dalam `LICENSE-CODE.txt`; batas hak, provenance, koreksi,
dan cacat hulu dijelaskan dalam `ATTRIBUTION.md`.

