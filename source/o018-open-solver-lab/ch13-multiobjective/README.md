# Pendamping terbuka Bab 13: optimisasi multiobjektif

Direktori ini menyediakan laboratorium O018 yang terpisah untuk seluruh 11
latihan Bab 13, *Optimisasi Multiobjektif*. Laboratorium mempertahankan data,
matematika, label latihan, dan urutan edisi Bahasa Indonesia R017, lalu memberi
sertifikat eksak serta pemeriksaan independen dengan Pyomo+HiGHS.

## Cakupan

- 11 dari 11 latihan dicakup dengan ID buku stabil `13.1` sampai `13.11`;
- label LaTeX asli (`ex:pareto-def` sampai `ex:furniture-weights`) disimpan
  bersama setiap hasil;
- ketidakselarasan manual dinyatakan terbuka: Latihan buku 13.10
  `ex:lex-vs-weighted` tidak ada dalam manual, sedangkan entri manual 13.10
  sebenarnya menjawab Latihan buku 13.11 `ex:furniture-weights`;
- dominasi, batas Pareto diskret, skor jumlah berbobot, selubung konveks,
  kendala-epsilon, laju kompromi, dan titik pisah bobot dihitung dengan
  `fractions.Fraction` bila nilainya rasional;
- model pilihan diskret dan PL kontinu diperiksa dengan antarmuka
  `appsi_highs`; tidak ada pemecah berpemilik;
- tiga SVG id-ID yang dapat diakses memvisualkan Latihan 13.4, 13.7, dan 13.9.

`expected-results.json` adalah orakel independen yang ditulis terpisah dari
mesin. `results.json` menyimpan sertifikat, seluruh pemeriksaan solver, pemetaan
buku--manual, cacat sumber yang diketahui, dan inventaris visual. Tidak ada
latihan yang dibiarkan tak terselesaikan; status tanpa solusi manual pada 13.10
tetap terlihat dan tidak ditutupi dengan penomoran ulang.

## Menjalankan secara offline

Dari akar lane, gunakan runtime CPython 3.12 yang dikunci:

```powershell
<python-terkunci> source/o018-open-solver-lab/ch13-multiobjective/run_lab.py
<python-terkunci> source/o018-open-solver-lab/ch13-multiobjective/run_lab.py --check
<python-terkunci> -m unittest discover -s source/o018-open-solver-lab/ch13-multiobjective -p "test_models.py" -v
<python-terkunci> source/o018-open-solver-lab/ch13-multiobjective/verify_receipt.py --check
```

Runtime lengkap dibekukan dalam `../requirements.lock` dan
`../runtime-receipt.json`. Laboratorium tidak memerlukan jaringan, Microsoft
Excel, Gurobi, CPLEX, atau pemecah berpemilik lain.

Prosa, data adaptasi, orakel, dan SVG mengikuti CC BY-SA 4.0. Kode Python baru
mengikuti Lisensi MIT dalam `LICENSE-CODE.txt`; batas hak dan provenance
dijelaskan dalam `ATTRIBUTION.md`.
