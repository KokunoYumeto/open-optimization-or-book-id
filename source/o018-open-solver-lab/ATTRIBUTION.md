# Atribusi dan hak komponen

## Soal dan model sumber

Laboratorium `ch01-shirt-ordering` mengadaptasi Latihan
`ex:shirt-full-lp` dan solusi terpilihnya dari *Mathematical Programming and
Operations Research, Book 1*, Robert Hildebrand dkk., pada komit sumber
`1745df89b608899f66983834fa4ec8c8910d18ff`:

`Intro-Math-Programming/baseText/book/part1-linear-programming/ch01-introduction/mathematicalProgramming.tex`

Konten dan gambar buku dinyatakan CC BY-SA 4.0 dalam `LICENSE-Content` pada
komit tersebut. Adaptasi penjelasan dan data soal di sini mengikuti CC BY-SA
4.0, mencantumkan sumber, dan menyatakan bahwa format komputasinya diubah dari
uraian/solusi buku menjadi model Pyomo yang dapat dieksekusi.

## Kode laboratorium

Kode baru di direktori ini tersedia menurut Lisensi MIT; lihat
`LICENSE-CODE.txt`. Kode ini adalah pendamping terpisah dan bukan klaim bahwa
seluruh buku berlisensi MIT.

## Runtime pihak ketiga

- Pyomo 6.10.1 — BSD-3-Clause.
  Sumber resmi: <https://github.com/Pyomo/pyomo/tree/6.10.1>.
- highspy/HiGHS 1.15.1 — MIT untuk paket standar tanpa ekstra HiPO.
  Sumber resmi: <https://github.com/ERGO-Code/HiGHS/tree/v1.15.1>.
- NumPy 2.5.2 — ekspresi lisensi paket
  `BSD-3-Clause AND 0BSD AND MIT AND Zlib AND CC0-1.0`; seluruh berkas lisensi
  yang dikemas dibekukan bersama receipt runtime.

Laboratorium tidak memasang `highspy[extras]`; dengan demikian dependensi HiPO
berlisensi Apache tidak termasuk dalam closure runtime ini. Paket standar
tetap membawa pemberitahuan komponen pihak ketiga untuk CLI11, pdqsort, dan
zstr; `LICENSE.txt` serta `THIRD_PARTY_NOTICES.md` dibekukan utuh dan tidak
diringkas sebagai closure “MIT saja”.
