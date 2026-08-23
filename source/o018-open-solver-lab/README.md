# Laboratorium Pemecah Terbuka O018

Laboratorium ini adalah pendamping terpisah untuk edisi Bahasa Indonesia
*Mathematical Programming and Operations Research, Book 1*. Tujuannya adalah
menyediakan jalur komputasi terbuka berbasis Pyomo dan HiGHS tanpa mengganti
matematika buku sumber, serta tanpa mewajibkan Microsoft Excel Solver atau
Gurobi.

## Laboratorium pertama

`ch01-shirt-ordering` menerapkan Latihan `ex:shirt-full-lp` dari Bab 1. Model
mempertahankan tepat tiga persamaan keseimbangan persediaan, biaya pemesanan,
biaya penyimpanan, dan syarat nonnegatif dari buku. Dua mode dijalankan:

- `lp`: semua variabel kontinu dan nonnegatif;
- `integer`: semua pesanan dan persediaan bernilai bilangan bulat nonnegatif.

Keduanya menghasilkan rencana yang sama: pesan 22 kaus pada hari Kamis, tidak
memesan lagi, dan biaya minimum 188.

Untuk menjalankan laboratorium dari direktorinya:

```powershell
python run_lab.py --mode both
python -m unittest -v test_model.py
```

Versi runtime yang diterima dibekukan dalam `requirements.lock`; resep dan
hasil yang diharapkan dibekukan dalam `data.json` dan
`expected-results.json`. `run_lab.py` menulis `results.json` secara
deterministik.

## Batas lisensi

Prosa yang mengadaptasi soal buku mengikuti CC BY-SA 4.0. Kode baru di
laboratorium ini tersedia menurut Lisensi MIT. Pyomo dan HiGHS tetap merupakan
komponen pihak ketiga dengan lisensinya masing-masing; lihat `ATTRIBUTION.md`.

