# Pendamping terbuka Bab 5: program linier grafis

Direktori ini menyediakan laboratorium Pyomo+HiGHS yang terpisah untuk 17
latihan Bab 5, *Menyelesaikan Program Linier secara Grafis*. Data koefisien,
batas variabel, arah pertidaksamaan, titik ekstrem, ruas optimum, dan
sertifikat sinar disimpan dalam bentuk terstruktur di `data.json`; kode tidak
mengekstrak matematika dari prosa saat dijalankan.

## Cakupan

- 16 latihan mempunyai model numerik yang dapat dieksekusi;
- Latihan 5.11 adalah argumen konseptual umum dan sengaja berstatus
  `parameter_required`; laboratorium tidak mereka-reka matriks, ruas kanan,
  atau fungsi tujuan;
- 19 skenario dipecahkan: dua analisis daerah, satu kasus tak layak, empat
  kasus objektif tak berbatas, lima kasus optimum jamak, dan tujuh kasus
  optimum tunggal;
- 18 plot SVG id-ID dihasilkan untuk semua skenario dua variabel. Latihan 5.10
  mempunyai tiga variabel sehingga tidak diproyeksikan secara sembarang;
  Latihan 5.11 tidak mempunyai geometri numerik.

Setiap SVG memuat `title`, `desc`, `role="img"`, bahasa `id-ID`, alternatif
teks terstruktur, dan pengungkapan bahwa jendela gambar bukan kendala model.
Renderer SVG lokal bersifat deterministik dan tidak memerlukan Matplotlib.

## Hasil utama yang dikunci

`expected-results.json` mempertahankan titik atau ruas optimum yang dinyatakan
sumber. Di antaranya:

- Latihan 5.5: seluruh ruas `(10,3)`--`(15,0)` optimal dengan nilai 45;
- Latihan 5.7: optimum `(11/5,-2/5)` dengan nilai `9/5`, tanpa batas
  nonnegativitas yang tidak ada dalam soal;
- Latihan 5.9: model sebagaimana tertulis tak berbatas; edisi Indonesia memakai
  judul netral “Berhingga atau Tak Berbatas?” agar judul tidak menyiratkan hasil
  berhingga yang keliru;
- Latihan 5.10: optimum LP `(110/191,280/191,0)` dengan biaya `11650/191` dan
  ruas kanan zat gizi yang sudah diperbaiki dalam authority tersemat;
- Latihan 5.12, 5.13, dan 5.17: seluruh ruas optimum dipertahankan, bukan
  direduksi menjadi satu titik yang kebetulan dipilih solver;
- Latihan 5.16: minimum 6 di `(1,2)` dan dua sertifikat maksimum tak berbatas,
  termasuk arah authority yang sudah diperbaiki `(2,1)`.

Daftar divergensi di `data.json` membedakan koreksi edisi Indonesia,
ketidakselarasan manual, dan fakta koreksi yang sudah terdapat dalam authority.
Tidak ada perubahan diam-diam pada matematika latihan dan tidak ada kontak
dengan penulis.

## Menjalankan secara offline

Dari akar lane, gunakan CPython 3.12 dan wheel yang sudah dibekukan:

```powershell
python -m venv <direktori-sementara>
<direktori-sementara>\Scripts\python.exe -m pip install --no-index --find-links=authority/runtime-wheels/windows-cp312-amd64 --require-hashes --only-binary=:all: -r source/o018-open-solver-lab/requirements.lock
<direktori-sementara>\Scripts\python.exe source/o018-open-solver-lab/ch05-graphical-lp/run_lab.py
<direktori-sementara>\Scripts\python.exe source/o018-open-solver-lab/ch05-graphical-lp/run_lab.py --check
<direktori-sementara>\Scripts\python.exe -m unittest discover -s source/o018-open-solver-lab/ch05-graphical-lp -p "test_models.py" -v
```

`run_lab.py --check` menyelesaikan ulang semua skenario dan membandingkan byte
`results.json` serta seluruh inventaris SVG tanpa menulis. Runtime tidak
memerlukan jaringan, Gurobi, CPLEX, Excel, atau pustaka berpemilik.

Prosa, data adaptasi, dan SVG mengikuti CC BY-SA 4.0. Kode Python baru
mengikuti Lisensi MIT di `LICENSE-CODE.txt`; rincian hak dan provenance ada di
`ATTRIBUTION.md`.
