# Atribusi dan hak komponen

## Soal, prosa, dan data adaptasi

Laboratorium ini mengadaptasi 17 latihan Bab 5, *Menyelesaikan Program Linier
secara Grafis*, dari *Mathematical Programming and Operations Research, Book
1*, Robert Hildebrand dkk., pada komit sumber
`1745df89b608899f66983834fa4ec8c8910d18ff`.

Authority yang dibekukan adalah:

- `Section2.tex`, 62.475 byte, SHA-256
  `9a095760e4983e71bc2cf840142aea3f1121f2236ff45f0248d3ca13970281d1`;
- `solutions-manual/ch05.tex`, 21.346 byte, SHA-256
  `e58a3b4fca24c1bc765b22c2db18b125e92731dd759bfd706d4028dd8d2eadaa`.

Closure terjemahan Indonesia yang menjadi saksi interpretasi adalah:

- `Section2.tex`, 65.226 byte, SHA-256
  `35c058e6af26b699a1cca70906f9ac41da804940b668101613f6994b9d8b00ff`;
- `solutions-manual/ch05.tex`, 22.684 byte, SHA-256
  `ee6db2bb15936c83159d0e97eafb19dc34e4914dd379bd774cf681fb961e640c`.

Path lengkap, peran, ukuran, dan hash terdapat di `data.json` dan diverifikasi
oleh uji unit. Konten dan gambar buku dinyatakan CC BY-SA 4.0 dalam
`LICENSE-Content` pada komit sumber. Bab tersebut juga mempertahankan atribusi
terlihat kepada Kevin Cheung untuk materi CC BY-SA 4.0 yang dimodifikasi oleh
Robert Hildebrand, serta kredit terlihat untuk gambar TikZ pinjaman. Gambar
TikZ pinjaman itu tidak disalin ke paket ini.

Prosa adaptasi di `README.md` dan `ATTRIBUTION.md`, data adaptasi di
`data.json` dan `expected-results.json`, serta SVG yang dihasilkan mengikuti
CC BY-SA 4.0. Format diubah dari soal, solusi, dan TikZ menjadi model numerik,
sertifikat, serta plot SVG yang dapat diuji. `results.json` adalah keluaran
faktual mesin; tidak ada klaim hak kreatif tambahan atas receipt atau log.

## Kode laboratorium

Kode baru `model.py`, `plot_svg.py`, `run_lab.py`, `test_models.py`, dan
`verify_receipt.py` tersedia menurut Lisensi MIT; lihat `LICENSE-CODE.txt`.
Lisensi MIT hanya berlaku pada kode baru dan tidak mengubah lisensi buku,
prosa/data adaptasi, atau SVG hasil adaptasi.

Renderer plot ditulis khusus untuk paket ini dengan pustaka standar Python.
Tidak ada Matplotlib, perangkat lunak jaringan, atau backend grafis pihak
ketiga yang diperlukan. Hak renderer karena itu tercakup oleh Lisensi MIT kode
baru.

## Runtime pihak ketiga yang dibekukan

- Pyomo 6.10.1 — BSD-3-Clause;
- highspy/HiGHS 1.15.1 — MIT untuk paket standar tanpa ekstra HiPO;
- NumPy 2.5.2 — `BSD-3-Clause AND 0BSD AND MIT AND Zlib AND CC0-1.0`.

Wheel dan hash dikunci oleh
`source/o018-open-solver-lab/requirements.lock`. Bukti lisensi lengkap berada
di `authority/runtime-licenses/`, dan manifest wheel berada di
`authority/runtime-wheels/`. Paket `highspy[extras]` tidak dipasang;
pemberitahuan pihak ketiga yang dibundel tetap berlaku utuh.

## Pemisahan dan catatan koreksi

Laboratorium ini bukan produk atau distribusi Gurobi, CPLEX, Microsoft Excel,
atau solver berpemilik lain. Tidak ada API, berkas, lisensi, maupun runtime
berpemilik yang dibundel atau dibutuhkan.

Enam koreksi edisi Indonesia, dua ketidakselarasan yang dipertahankan, dan dua
fakta perbaikan yang sudah terdapat dalam authority diberi ID serta status
terpisah di `data.json`. Khususnya, model Latihan 5.9 tidak diubah agar sesuai
dengan judulnya, Latihan 5.11 tetap gagal tertutup, dan perbaikan Latihan 5.10
serta 5.16 tidak diklaim sebagai koreksi baru laboratorium.
