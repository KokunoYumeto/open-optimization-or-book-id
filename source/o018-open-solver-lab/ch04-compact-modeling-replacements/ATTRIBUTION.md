# Atribusi dan hak komponen

## Soal, prosa, dan data adaptasi

Laboratorium ini mengadaptasi keluarga model operasional dalam Bab 4,
*Pemodelan dengan Notasi Ringkas*, dari *Mathematical Programming and
Operations Research, Book 1*, Robert Hildebrand dkk., pada komit sumber
`1745df89b608899f66983834fa4ec8c8910d18ff` dan tree
`209d5de696ebac4e5921b73d6b6b2f539fc23d1c`.

Dua berkas bab authority yang dibekukan adalah:

- `modeling-sums.tex`, 40.459 byte, SHA-256
  `b549fb1399f98744b5485a0b064b54238485166f5456fabc4ea898778750c630`;
- `modeling-sums-continued.tex`, 80.405 byte, SHA-256
  `7ebb3e77a83b05ddb51e8009072ea11b92ff566af58f539c5b80a576c2f06f55`.

Closure operasional membekukan 11 workbook XLSX dan 22 notebook pasangan
PuLP/Gurobi pada komit yang sama. Saksi CSV bus sekolah dibekukan dari
`open-optimization-or-examples@b924d2fe61ee0ba925903aba615db4f46e65b4be`
dengan ukuran 163 byte dan SHA-256
`8caa2666672c507cf1317fcf87c2c66e2a1705c914573a6b87c80dfca5119817`.
Daftar lengkap 36 berkas, path, ukuran, dan SHA-256 berada di
`data.json` → `provenance.source_files`; uji unit memverifikasi setiap byte.

Konten dan gambar buku dinyatakan CC BY-SA 4.0 dalam `LICENSE-Content` pada
komit sumber. Prosa adaptasi di `README.md` dan `ATTRIBUTION.md`, serta data
adaptasi di `data.json` dan `expected-results.json`, mengikuti CC BY-SA 4.0.
Format diubah dari workbook/notebook berpemilik atau khusus-pemecah menjadi
data dan model terbuka yang dapat dieksekusi.

Data bus sekolah dalam laboratorium diadaptasi dari tabel buku yang berlisensi
CC BY-SA 4.0. Snapshot CSV eksternal berfungsi sebagai saksi provenance saja.
Snapshot repositori eksternal tersebut tidak mempunyai berkas lisensi lokal
yang ditemukan, sehingga laboratorium tidak mengandalkannya sebagai dasar hak
untuk prosa atau data adaptasi dan tidak menyalin CSV itu ke paket ini.

`results.json` adalah keluaran faktual mesin. Tidak ada klaim hak kreatif
tambahan atas tanda terima atau log verifikasi.

## Kode laboratorium

Kode baru `model.py`, `run_lab.py`, dan `test_models.py` tersedia menurut
Lisensi MIT; lihat `LICENSE-CODE.txt`. Lisensi MIT ini hanya berlaku pada kode
baru tersebut dan tidak mengubah lisensi prosa, data adaptasi, sumber buku,
workbook, atau notebook.

## Pemisahan dari perangkat lunak lain

Laboratorium ini bukan produk, plugin, atau distribusi Microsoft Excel,
Microsoft Excel Solver, PuLP, maupun Gurobi. Nama-nama itu disebut hanya untuk
menjelaskan closure sumber dan divergensinya. Tidak ada berkas, API, lisensi,
atau runtime berpemilik yang dibundel atau dibutuhkan.

## Runtime pihak ketiga yang dibekukan

- Pyomo 6.10.1 — BSD-3-Clause.
- highspy/HiGHS 1.15.1 — MIT untuk paket standar tanpa ekstra HiPO.
- NumPy 2.5.2 — `BSD-3-Clause AND 0BSD AND MIT AND Zlib AND CC0-1.0`.

Wheel dan hash dikunci oleh
`source/o018-open-solver-lab/requirements.lock`. Bukti lisensi lengkap berada
di `authority/runtime-licenses/`, dan manifest wheel berada di
`authority/runtime-wheels/`. Paket `highspy[extras]` tidak dipasang;
pemberitahuan pihak ketiga yang dibundel tetap berlaku utuh.

## Catatan koreksi

Enam divergensi dikunci di `data.json`: arah busur `d->b`, terminal maskapai
`d->t` dan nilai 12, arah/aliran/biaya multikomoditas 45, kapasitas lembur yang
hilang, semantik investasi yang belum selesai, serta laporan workbook
penugasan 129 yang bertentangan dengan jumlah benar 98. Tiga yang lengkap
diterapkan sebagai koreksi; dua yang belum mempunyai data atau semantik diberi
status tidak dapat dieksekusi; tidak ada nilai yang direka.
