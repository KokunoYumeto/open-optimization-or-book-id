# Pendamping terbuka Bab 7–9: klaster simpleks

Direktori ini adalah laboratorium O018 yang terpisah untuk seluruh 38 latihan
klaster simpleks: Bab 7 (*Metode Simpleks*), Bab 8 (*Simpleks — Perhitungan
Matriks*), dan Bab 9 (*Metode Simpleks dalam Bentuk Tableau*). Laboratorium
tidak mengubah buku R017. Data diadaptasi dari enam bab/manual authority dan
enam saksi terjemahan Indonesia yang hash-nya dibekukan dalam `data.json`.

## Cakupan

- 38 dari 38 latihan diverifikasi: 17 pada Bab 7, 9 pada Bab 8, dan 12 pada
  Bab 9; tidak ada latihan yang kekurangan data;
- `fractions.Fraction` mempertahankan bentuk standar, solusi basis, invers,
  biaya tereduksi, kamus, uji rasio, dan setiap pivot secara eksak;
- lintasan penuh basis/nonbasis/RHS/biaya tereduksi disimpan untuk 7.7–7.13,
  sedangkan 9.4–9.7 menyimpan tableau setelah setiap pivot;
- koefisien Big-M direpresentasikan sebagai pasangan simbolik rasional
  `(koefisien M, konstanta)`, bukan dengan memilih angka M yang sewenang-wenang;
- 16 pemanggilan Pyomo+HiGHS memberi pemeriksaan independen: 15 optimum dan
  satu klasifikasi tak terbatas; pelanggaran maksimum yang diterima adalah
  `1e-8`;
- soal pembuktian memakai identitas atau sertifikat langsung. Latihan 9.10 dan
  9.11 hanya memberi tableau, sehingga laboratorium sengaja tidak mereka-reka
  program linier asal;
- tiga SVG id-ID yang dapat diakses disediakan hanya ketika geometri menambah
  nilai pedagogis: basis/pivot 7.15, hasil imbang degenerat 7.17, dan sinar tak
  terbatas 9.12.

`expected-results.json` adalah oracle yang ditulis terpisah dari mesin.
`results.json` menyimpan hasil lengkap, termasuk setiap kamus/tableau antara,
rasio, hasil imbang, basis, biaya tereduksi, dan sertifikat.

## Menjalankan secara offline

Dari akar lane, buat runtime CPython 3.12 dari wheel yang sudah dibekukan:

```powershell
python -m venv <direktori-sementara>
<direktori-sementara>\Scripts\python.exe -m pip install --no-index --find-links=authority/runtime-wheels/windows-cp312-amd64 --require-hashes --only-binary=:all: -r source/o018-open-solver-lab/requirements.lock
<direktori-sementara>\Scripts\python.exe source/o018-open-solver-lab/ch07-ch09-simplex/run_lab.py
<direktori-sementara>\Scripts\python.exe source/o018-open-solver-lab/ch07-ch09-simplex/run_lab.py --check
<direktori-sementara>\Scripts\python.exe -m unittest discover -s source/o018-open-solver-lab/ch07-ch09-simplex -p "test_models.py" -v
<direktori-sementara>\Scripts\python.exe source/o018-open-solver-lab/ch07-ch09-simplex/verify_receipt.py --check
```

`run_lab.py --check` menghitung ulang semua hasil dan membandingkan byte JSON
serta inventaris SVG tanpa menulis. `verify_receipt.py --check` juga
meregenerasi dua kali di memori, mengunci semua artifact, memeriksa closure
runtime, dan menolak receipt yang usang.

Prosa, data adaptasi, oracle, dan SVG mengikuti CC BY-SA 4.0. Kode Python baru
mengikuti Lisensi MIT di `LICENSE-CODE.txt`. Batas hak dan pemberitahuan runtime
lengkap terdapat di `ATTRIBUTION.md`.

