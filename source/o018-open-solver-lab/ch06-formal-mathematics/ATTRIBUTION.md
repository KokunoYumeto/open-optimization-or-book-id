# Atribusi dan hak komponen

## Soal, prosa, dan data adaptasi

Laboratorium ini mengadaptasi 12 latihan Bab 6, *Pernyataan Matematis Formal*,
dari *Mathematical Programming and Operations Research, Book 1*, Robert
Hildebrand dkk., pada komit sumber
`1745df89b608899f66983834fa4ec8c8910d18ff`.

Empat saksi sumber yang dibekukan adalah:

- bab authority: 50.024 byte, SHA-256
  `26c5a18526e75e869fea5e18591f095bbb642659d6c7df04bbb45564e5861803`;
- manual authority: 14.069 byte, SHA-256
  `81f818aa9630e4f421171f745a5b31084f509465efcd9eb754e7545c9e1694e1`;
- bab terjemahan Indonesia: 52.190 byte, SHA-256
  `4e08b0c7d3b5e89a868800569eeb57b9128d6b1b009301ce0cd2fcae9c2e75ca`;
- manual terjemahan Indonesia: 15.677 byte, SHA-256
  `3f54164435b4fe489e907b8ebfc71c862ff09a73af288d427830db84feefd344`.

Path lengkap, peran, ukuran, dan hash yang sama terdapat di `data.json`.
Uji unit membaca keempat berkas hidup, memeriksa byte/hash, dan memastikan
bahwa setiap identitas terlihat di atas tetap sama dengan data mesin.

Konten buku dinyatakan CC BY-SA 4.0 dalam `LICENSE-Content` pada komit sumber.
Prosa adaptasi di `README.md` dan `ATTRIBUTION.md`, data adaptasi di `data.json`
dan `expected-results.json`, serta SVG yang dihasilkan mengikuti CC BY-SA 4.0.
Format diubah dari soal, solusi, dan TikZ menjadi data terstruktur, komputasi,
sertifikat pembuktian, dan visual SVG yang dapat diuji. `results.json` adalah
keluaran faktual mesin; tidak ada klaim hak kreatif tambahan atas receipt atau
log verifikasi.

## Kode laboratorium

Kode baru `model.py`, `plot_svg.py`, `run_lab.py`, `test_models.py`, dan
`verify_receipt.py` tersedia menurut Lisensi MIT; lihat `LICENSE-CODE.txt`.
Lisensi MIT hanya berlaku pada kode baru dan tidak mengubah lisensi buku,
prosa/data adaptasi, atau SVG hasil adaptasi.

## Runtime pihak ketiga yang dibekukan

- Pyomo 6.10.1 — BSD-3-Clause;
- highspy/HiGHS 1.15.1 — MIT untuk paket standar tanpa ekstra HiPO;
- NumPy 2.5.2 — `BSD-3-Clause AND 0BSD AND MIT AND Zlib AND CC0-1.0`.

Versi dan hash wheel dikunci oleh
`source/o018-open-solver-lab/requirements.lock`. Bukti lisensi lengkap berada
di `authority/runtime-licenses/`, manifest wheel berada di
`authority/runtime-wheels/`, dan closure runtime diringkas dalam
`source/o018-open-solver-lab/runtime-receipt.json`. Renderer SVG memakai hanya
pustaka standar Python dan termasuk kode MIT paket ini.

Laboratorium ini bukan produk atau distribusi Gurobi, CPLEX, Microsoft Excel,
atau pemecah berpemilik lain. Tidak ada API, berkas, lisensi, maupun runtime
berpemilik atau jaringan yang dibundel atau dibutuhkan.

## Koreksi dan batas interpretasi

Tidak ada koreksi matematis baru yang diterapkan oleh laboratorium ini dan
tidak ada data latihan yang dilengkapi secara imajinatif. Pemeriksaan satu
titik tengah pada Latihan 6.7 diperlakukan sebagai ilustrasi, sedangkan
konveksitas setengah ruang dibuktikan oleh identitas linear umum. Soal-soal
6.10--6.12 dipertahankan sebagai pembuktian umum dengan sertifikat langkah,
bukan diubah menjadi satu contoh numerik yang lebih sempit.
