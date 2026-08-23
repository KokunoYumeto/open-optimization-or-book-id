# Pendamping terbuka Bab 4: pemodelan ringkas

Direktori ini menyediakan adaptasi Pyomo+HiGHS yang dapat diulang untuk
keluarga model operasional pada Bab 4, *Pemodelan dengan Notasi Ringkas*.
Laboratorium ini adalah pendamping terbuka yang terpisah: bukan salinan
antarmuka Excel, bukan konversi notebook PuLP, dan bukan integrasi Gurobi.

## Cakupan dan hasil acuan

| Keluarga pada sumber | Status laboratorium | Hasil acuan |
|---|---|---|
| Produksi 10 periode | dapat dieksekusi | biaya 1240 |
| Produksi dengan lembur | memerlukan parameter | kapasitas reguler dan lembur belum diberikan sumber |
| Penugasan mesin | dapat dieksekusi | biaya 13 |
| Penugasan bus sekolah | dapat dieksekusi | biaya 325 |
| Penugasan orang-ke-tugas | dapat dieksekusi | biaya 98 |
| Deviasi mutlak | dapat dieksekusi | median 5; deviasi total 7 |
| Aliran biaya minimum gudang-ke-toko | dapat dieksekusi | biaya 180 |
| Aliran maksimum maskapai | dapat dieksekusi setelah koreksi | aliran 12; cut pembukti 12 |
| Aliran multikomoditas bilangan bulat | dapat dieksekusi setelah koreksi | biaya 45 |
| Aliran multikomoditas sumber--tujuan | dapat dieksekusi | biaya 51 |
| Investasi multiperiodik | desain belum selesai | tidak dijalankan |

Sebagai saksi tambahan bagi rumusan cetak dan konvensi tandanya, laboratorium
juga menjalankan jaringan biaya minimum tak terstruktur dengan busur yang benar
`d->b`; biaya minimumnya 140. Dengan demikian terdapat sepuluh pemecahan: sembilan
kasus tautan operasional yang lengkap dan satu saksi rumusan cetak tambahan.
Dua kasus tautan lainnya sengaja tidak dijalankan.

`data.json` membekukan koefisien, domain, status eksekusi, dua konvensi tanda,
36 sumber beserta hash-nya, dan enam catatan divergensi.
`expected-results.json` adalah kontrak angka. `results.json` dibuat oleh
`run_lab.py`; opsi `--check` menyelesaikan ulang seluruh kasus yang dapat
dieksekusi tanpa menulis dan menuntut kecocokan byte penuh.

## Dua konvensi tanda yang tidak boleh dicampur

Bab ini memang memakai dua konvensi yang berbeda, dan laboratorium
mempertahankannya secara eksplisit:

- jika nilai positif berarti **pasokan**, gunakan `keluar - masuk = pasokan`;
- jika nilai positif berarti **permintaan**, gunakan `masuk - keluar = permintaan`.

Jaringan tak terstruktur dan model multikomoditas bilangan bulat memakai
konvensi kedua. Rumusan sumber--tujuan memakai bentuk satuan yang setara:
`keluar - masuk` bernilai 1 di sumber, -1 di tujuan, dan 0 di simpul transit.
Uji regresi menghitung kembali keseimbangan ini dari hasil aliran.

## Kasus yang sengaja gagal tertutup

### Produksi dengan lembur

Model, workbook, dan kedua notebook sumber mempunyai biaya reguler dan lembur,
tetapi tidak mempunyai batas kapasitas. Karena biaya lembur selalu lebih tinggi,
model tanpa kapasitas tidak pernah memerlukan lembur dan tidak menguji keputusan
yang dinyatakannya. `build_production_overtime()` karena itu menolak eksekusi
tanpa dua vektor eksplisit: `regular_capacity[1..10]` dan
`overtime_capacity[1..10]`.

### Investasi multiperiodik

Soal meminta LP, sedangkan solusi dan aset memakai pilihan 0--1. Rumusan itu
juga menghapus kas yang tidak dibelanjakan ketika berpindah periode, tidak
menetapkan apakah peluang dapat diulang, dan masih memuat TODO sumber tentang
domain variabel. `build_multi_period_investment()` karena itu selalu menolak
eksekusi sampai semantik desain tersebut diputuskan. Laboratorium tidak
menampilkan optimum dari model biner yang belum selesai seolah-olah itulah
jawaban soal.

## Koreksi dan divergensi terikat

Laboratorium menerapkan matematika cetak yang sudah dikoreksi dan mencatat
perbedaannya terhadap aset lama:

1. jaringan tak terstruktur memakai `d->b`, bukan `b->d` yang tidak layak;
2. jaringan maskapai memakai `d->t` berkapasitas 7 dan maksimum 12, bukan
   `d->e` dan maksimum 9 dari workbook/notebook lama;
3. contoh multikomoditas memakai arah `1->3`, aliran layak, dan biaya 45;
4. produksi lembur tetap menunggu kapasitas, bukan diberi angka rekaan;
5. investasi tetap berstatus `design_unresolved`;
6. laporan jawaban workbook penugasan menyatakan 129, padahal sel pilihannya
   sendiri berjumlah `38 + 33 + 27 = 98`; laboratorium memakai 98.

Rincian yang dapat diproses mesin ada pada `data.json` di bawah
`divergences`. Tidak ada pesan yang dikirim kepada penulis.

## Solusi degenerat

Aliran maksimum mempunyai beberapa vektor busur optimal. Kontrak numeriknya
memeriksa nilai tujuan, aliran sumber/tujuan, kelayakan, dan kapasitas cut 12,
bukan memaksakan satu vektor busur tertentu. Pada model multikomoditas pecahan,
pemisahan aliran agregat di antara dua komoditas juga tidak tunggal;
`results.json` hanya menyimpan aliran agregat yang relevan dan menyatakan bahwa
rute per komoditas sengaja dihilangkan.

## Menjalankan secara offline

Dari akar lane, buat lingkungan CPython 3.12 sekali pakai dan pasang hanya dari
wheel yang sudah dibekukan:

```powershell
python -m venv <direktori-sementara>
<direktori-sementara>\Scripts\python.exe -m pip install --no-index --find-links=authority/runtime-wheels/windows-cp312-amd64 --require-hashes --only-binary=:all: -r source/o018-open-solver-lab/requirements.lock
<direktori-sementara>\Scripts\python.exe source/o018-open-solver-lab/ch04-compact-modeling-replacements/run_lab.py
<direktori-sementara>\Scripts\python.exe source/o018-open-solver-lab/ch04-compact-modeling-replacements/run_lab.py --check
<direktori-sementara>\Scripts\python.exe -m unittest discover -s source/o018-open-solver-lab/ch04-compact-modeling-replacements -p "test_models.py" -v
```

Tidak diperlukan jaringan, Microsoft Excel, PuLP, atau Gurobi. Semua model yang
dijalankan memakai `SolverFactory("appsi_highs")` dengan Pyomo 6.10.1,
highspy/HiGHS 1.15.1, dan NumPy 2.5.2 dari closure wheel lokal.

Hak komponen dan provenance terperinci ada di `ATTRIBUTION.md`. Prosa dan data
adaptasi mengikuti CC BY-SA 4.0; kode Python baru mengikuti Lisensi MIT di
`LICENSE-CODE.txt`.
