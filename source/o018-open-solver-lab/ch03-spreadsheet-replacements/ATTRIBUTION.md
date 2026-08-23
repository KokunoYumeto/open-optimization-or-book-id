# Atribusi dan hak komponen

## Soal, prosa, dan data adaptasi

Laboratorium ini mengadaptasi peran matematis Latihan 3.1--3.9 beserta solusi
terpilih dari *Mathematical Programming and Operations Research, Book 1*,
Robert Hildebrand dkk., pada komit sumber
`1745df89b608899f66983834fa4ec8c8910d18ff`.

Sumber terjemahan Indonesia yang dibekukan untuk adaptasi ini adalah:

- `source/Intro-Math-Programming/baseText/book/part1-linear-programming/ch03-software/software-excel.tex`,
  SHA-256 `a38b55c6ffd45a60b0b225c5fd9807628c17bbc39201efac588fbe760dae5a70`;
- `source/Intro-Math-Programming/baseText/book/solutions-manual/ch03.tex`,
  SHA-256 `847c8b25bcca57a0d20c15f7b46ce81ddb72e4a76a8d2421cd057b4c765eed15`.

Konten dan gambar buku dinyatakan CC BY-SA 4.0 dalam `LICENSE-Content` pada
komit sumber tersebut. Prosa adaptasi di `README.md` dan `ATTRIBUTION.md`, serta
data adaptasi di `data.json` dan `expected-results.json`, mengikuti CC BY-SA
4.0. Formatnya
diubah dari latihan berbasis lembar kerja menjadi data dan model terbuka yang
dapat dieksekusi. `results.json` adalah keluaran faktual mesin dari data itu;
tidak ada klaim hak kreatif tambahan atas tanda terima atau log verifikasi.

## Kode laboratorium

Kode baru `model.py`, `run_lab.py`, dan `test_models.py` tersedia menurut
Lisensi MIT; lihat `LICENSE-CODE.txt`. Lisensi MIT ini hanya berlaku pada kode
baru tersebut dan tidak mengubah lisensi prosa, data adaptasi, atau buku.

## Pemisahan dari perangkat lunak proprieter

Laboratorium ini bukan produk, plugin, atau distribusi Microsoft Excel,
Microsoft Excel Solver, maupun Gurobi. Nama antarmuka tersebut disebut hanya
untuk menjelaskan konteks latihan sumber. Tidak ada berkas, API, lisensi, atau
runtime proprieter yang dibundel atau dibutuhkan.

## Runtime pihak ketiga yang dibekukan

- Pyomo 6.10.1 — BSD-3-Clause.
- highspy/HiGHS 1.15.1 — MIT untuk paket standar tanpa ekstra HiPO.
- NumPy 2.5.2 — `BSD-3-Clause AND 0BSD AND MIT AND Zlib AND CC0-1.0`.

Wheel dan hash dikunci oleh `source/o018-open-solver-lab/requirements.lock`.
Bukti lisensi lengkap berada di `authority/runtime-licenses/`, dan manifest
wheel berada di `authority/runtime-wheels/`. Paket `highspy[extras]` tidak
dipasang; pemberitahuan pihak ketiga yang dibundel tetap berlaku utuh.
