# Atribusi, provenance, dan hak komponen

## Soal, manual, prosa, dan data adaptasi

Laboratorium ini mengadaptasi 38 latihan klaster simpleks dari *Mathematical
Programming and Operations Research, Book 1*, Robert Hildebrand dkk., pada
komit sumber `1745df89b608899f66983834fa4ec8c8910d18ff`.

Dua belas saksi yang dibekukan adalah:

- bab authority Bab 7: 132.627 byte, SHA-256
  `925e23f06a5c5900f4e61c416d6f624b57ab6581ae42696e09cf2e9892c19021`;
- manual authority Bab 7: 20.547 byte, SHA-256
  `e2068bcaf5538f47009f2e420907baabbc559d3c175ddb2443c352e1513f0b4b`;
- bab authority Bab 8: 37.596 byte, SHA-256
  `f012408ddcc285dc717c4156338fc9f315be9290122efdd0bad0cde704e5cec4`;
- manual authority Bab 8: 12.614 byte, SHA-256
  `7e374e3f0282398ee5150582735978637490d4d95328fe309bfed5580edc7fa6`;
- bab authority Bab 9: 30.290 byte, SHA-256
  `a99da17f6820e2e955f34c9db08f354c211b90ebf87cb2027bcf6660caca7b0b`;
- manual authority Bab 9: 14.072 byte, SHA-256
  `d5f7d7296e1b162ab74031a86d4d1e45da2a07891c992b50b2ab9fe57271ca65`;
- bab terjemahan Bab 7: 136.847 byte, SHA-256
  `b18eac29969fdce112da5ceb83b74518138d1bcaa22efe52aeee2411676b9b7c`;
- manual terjemahan Bab 7: 21.264 byte, SHA-256
  `bff78cc451540559fa73eb619ae0f71e86bfd0df9575e3dd50cea0faf56ae98d`;
- bab terjemahan Bab 8: 39.468 byte, SHA-256
  `1e0ac6ecd971c245bf090c82dcc4779b06cdd9e716004632138c4094c0430bf2`;
- manual terjemahan Bab 8: 12.946 byte, SHA-256
  `c19558f01e860afdf475157fda8af00ca3e5a08314cb188a5b3c9bc7046a7885`;
- bab terjemahan Bab 9: 30.803 byte, SHA-256
  `6fe55f1e5eac82caf2128f7cae220bb29ff9537802465cb9b28feb6bab1330de`;
- manual terjemahan Bab 9: 15.079 byte, SHA-256
  `f563b1aabe4d56830afbfb882e677d65ad890145c2a668d7dc31631d8baa7cb4`.

Path, peran, ukuran, dan hash yang sama tersedia dalam `data.json`. Uji unit
membaca semua saksi hidup dan menolak perubahan satu byte pun.

Konten buku dinyatakan CC BY-SA 4.0 dalam `LICENSE-Content` pada komit sumber.
Prosa adaptasi di `README.md` dan `ATTRIBUTION.md`, data di `data.json`, oracle
di `expected-results.json`, serta tiga SVG mengikuti CC BY-SA 4.0. Formatnya
berubah dari LaTeX/TikZ dan solusi naratif menjadi data terstruktur, aljabar
rasional yang dapat diuji, lintasan pivot, dan SVG yang dapat diakses.
`results.json`, log, serta receipt adalah keluaran faktual; tidak ada klaim hak
kreatif tambahan atas byte tersebut.

## Kode laboratorium

Kode baru `model.py`, `plot_svg.py`, `run_lab.py`, `test_models.py`, dan
`verify_receipt.py` tersedia menurut Lisensi MIT; lihat `LICENSE-CODE.txt`.
Lisensi MIT hanya berlaku pada kode baru dan tidak mengubah lisensi konten buku,
prosa/data adaptasi, oracle, atau SVG.

## Runtime pihak ketiga yang dibekukan

- Pyomo 6.10.1 — BSD-3-Clause;
- highspy/HiGHS 1.15.1 — MIT untuk paket standar tanpa ekstra HiPO;
- NumPy 2.5.2 — `BSD-3-Clause AND 0BSD AND MIT AND Zlib AND CC0-1.0`.

Versi dan hash wheel dikunci oleh
`source/o018-open-solver-lab/requirements.lock`. Bukti lisensi lengkap berada
di `authority/runtime-licenses/`, manifest wheel berada di
`authority/runtime-wheels/`, dan closure runtime diringkas dalam
`source/o018-open-solver-lab/runtime-receipt.json`. Renderer SVG hanya memakai
pustaka standar Python dan merupakan bagian kode MIT paket ini.

Laboratorium ini tidak memerlukan jaringan, Excel, Gurobi, CPLEX, Mosek, atau
pemecah berpemilik lain.

## Divergensi dan batas interpretasi

Tidak ada koreksi matematis O018 dan tidak ada data yang dilengkapi secara
imajinatif. Tiga perbedaan judul antara bab dan manual dipertahankan secara
eksplisit dalam `data.json`: manual 7.12 dan 7.13 menambahkan “(Big-M)”, dan
manual 8.8 memendekkan “aturan variabel masuk” menjadi “aturan masuk”.

Latihan 7.17 memang meminta pembaca membuat contoh lain; contoh kecil yang
disimpan paket adalah jawaban konstruktif terhadap permintaan itu, bukan
pengganti data sumber. Latihan 9.10 dan 9.11 hanya menyediakan tableau, sehingga
sertifikat dibatasi pada informasi tableau dan tidak merekonstruksi PL asal.
