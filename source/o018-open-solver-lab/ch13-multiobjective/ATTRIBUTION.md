# Atribusi, provenance, ketidakselarasan sumber, dan hak komponen

## Soal, manual, prosa, dan data adaptasi

Laboratorium ini mengadaptasi 11 latihan Bab 13, *Optimisasi Multiobjektif*,
dari *Mathematical Programming and Operations Research, Book 1*, Robert
Hildebrand dkk., pada komit sumber
`1745df89b608899f66983834fa4ec8c8910d18ff`.

Empat saksi hidup yang dibekukan adalah:

- bab otoritas: 40.340 byte, SHA-256
  `d3d83cb13eb0b34433551b1ed228c51dcbc062ab90f125049c7f323a3cf065b3`;
- manual otoritas: 18.634 byte, SHA-256
  `ac488fb2021c8b9a561afca4ab409c2584b2f4acec0e05928cd85da3bf781a15`;
- bab terjemahan Indonesia: 43.484 byte, SHA-256
  `fff540c73cf9f90fd0915f6cd65a4a02f330e60f01d89a14f72557aff0d6d274`;
- manual terjemahan Indonesia: 20.251 byte, SHA-256
  `2988e24b31d3c3acf0a86908cef02298237c9df4b2fd6e184ff2fe77aa4f5680`.

Jalur, peran, ukuran, dan hash yang sama terdapat dalam `data.json`. Uji unit
membaca keempat berkas hidup dan menolak perubahan satu byte pun.

Konten buku dinyatakan CC BY-SA 4.0 dalam `LICENSE-Content` pada komit sumber.
Prosa adaptasi, data, orakel, dan SVG laboratorium mengikuti CC BY-SA 4.0.
`results.json`, resi, dan log adalah keluaran faktual; tidak ada klaim hak
kreatif tambahan atas byte tersebut.

## Pemetaan buku--manual yang tidak boleh disamarkan

Bab buku memiliki 11 latihan. Manual menyatakan hanya sepuluh dan melewatkan
latihan berlabel `ex:lex-vs-weighted`. Karena itu:

- buku 13.1--13.9 selaras dengan manual 13.1--13.9;
- buku 13.10 (`ex:lex-vs-weighted`) berstatus `missing_from_manual`;
- buku 13.11 (`ex:furniture-weights`) berstatus `manual_stale_alias` dan
  dijawab oleh entri manual yang masih bernomor 13.10.

Laboratorium memakai ID buku 13.1--13.11 sebagai kunci utama. Nomor manual
hanya metadata; tidak ada penomoran ulang diam-diam.

## Cacat sumber berkeyakinan tinggi yang dipertahankan sebagai provenance

1. `DEF-CH13-MANUAL-OMISSION`: ketidakselarasan 11 latihan buku versus 10
   solusi manual sebagaimana dijelaskan di atas.
2. `DEF-CH13-70PCT-FIGURE`: poligon berlabel sedikitnya 70% dari pendapatan
   maksimum memakai `(8.5,0)` dan `(5,14)`, yang keduanya memberi pendapatan
   68.000, bukan `0.7*96.000 = 67.200`. Perpotongan tepat garis 70% adalah
   `(8.4,0)` dan `(34/7,496/35)`. Laboratorium tidak mengubah gambar sumber.
3. `DEF-CH13-REVENUE-PROFIT-TERMS`: tujuan `8000x+2000y` diperkenalkan sebagai
   pendapatan, tetapi beberapa paragraf berikutnya menyebut nilai yang sama
   sebagai laba tanpa memodelkan biaya.

Ketiga catatan disimpan dalam `data.json` dan `results.json`. Catatan ini bukan
koreksi baru terhadap jawaban latihan, dan tidak ada kontak dengan penulis.

## Kode dan runtime pihak ketiga

Kode baru `model.py`, `plot_svg.py`, `run_lab.py`, `test_models.py`, dan
`verify_receipt.py` tersedia menurut Lisensi MIT; lihat `LICENSE-CODE.txt`.
Lisensi ini tidak mengubah lisensi konten buku, data adaptasi, orakel, atau SVG.

- Pyomo 6.10.1 — BSD-3-Clause;
- highspy/HiGHS 1.15.1 — MIT untuk paket standar tanpa ekstra HiPO;
- NumPy 2.5.2 — `BSD-3-Clause AND 0BSD AND MIT AND Zlib AND CC0-1.0`.

Versi dan hash wheel dikunci dalam `../requirements.lock`; bukti lisensi dan
manifest wheel berada di `authority/runtime-licenses/` dan
`authority/runtime-wheels/`. Perender SVG hanya memakai pustaka standar
Python dan termasuk kode MIT paket ini.
