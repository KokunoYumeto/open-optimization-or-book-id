# Pendamping terbuka Bab 3: pengganti lembar kerja

Direktori ini menyediakan laboratorium Pyomo yang dapat diulang untuk peran
matematis Latihan 3.1--3.9. Laboratorium ini merupakan pendamping terbuka yang terpisah, bukan
salinan antarmuka Microsoft Excel Solver dan bukan integrasi Gurobi. Semua LP
yang dapat dieksekusi menggunakan `SolverFactory("appsi_highs")` dengan
Pyomo 6.10.1, highspy/HiGHS 1.15.1, dan NumPy 2.5.2 dari closure wheel lokal.

## Cakupan dan hasil acuan

| Latihan | Peran model | Hasil acuan |
|---|---|---|
| 3.1 | jaringan biaya minimum dengan kapasitas rute | biaya 160 |
| 3.2 | produksi sepuluh periode | biaya 1252; persediaan akhir tiap periode nol |
| 3.3 | diet kontinu | biaya 3.1677325983 |
| 3.4 | produksi dua produk dan sensitivitas koefisien objektif | `widget=50/3`, `gadget=20/3`, laba `520/3`; dual `10/3` dan `4/3` |
| 3.5 | transportasi seimbang tanpa kapasitas rute | biaya 300 |
| 3.6 | furnitur, dual, biaya tereduksi, dan penyelesaian ulang | laba 4100; dual sumber daya `(15, 5, 0)`; biaya tereduksi meja kerja `-15` |
| 3.7 | transportasi tak seimbang dan harga bayangan kapasitas | biaya 560; dual pasokan `(0, -2, 0)` |
| 3.8 | perbandingan konseptual metode pemecah | tidak ada model numerik tambahan |
| 3.9 | checkbox nonnegatif, variabel bebas, dan short selling | laba 12 tanpa short selling; 14.8 dengan `A=-40`, `B=140` |

`data.json` membekukan semua koefisien, domain, asumsi, dan provenance.
`expected-results.json` adalah kontrak angka. `results.json` dibuat oleh
`run_lab.py`; opsi `--check` menyelesaikan ulang semua model tanpa menulis dan
menuntut kecocokan byte penuh.

## Asumsi pemodelan

- Semua kuantitas keputusan kontinu. Hanya aset A pada mode checkbox
  nonnegatif yang dimatikan di Latihan 3.9 memakai domain `Reals`; variabel
  lainnya nonnegatif.
- Kendala pasokan transportasi ditulis sebagai kapasitas `<=`, sedangkan
  permintaan harus dipenuhi dengan persamaan. Pada Latihan 3.5 jumlah pasokan
  sama dengan jumlah permintaan, tetapi tidak ada kapasitas per rute.
- Latihan 3.7 mempunyai lebih dari satu vektor aliran optimal. Keluaran karena
  itu tidak mengklaim vektor rute atau total per pabrik sebagai solusi unik;
  laboratorium hanya menyerialkan besaran yang tidak berubah dan dual pasokan
  yang diminta. Karena itu, hasil untuk bagian ini sengaja tidak menjawab
  pabrik mana yang menanggung 10 unit kapasitas menganggur pada satu solusi
  dasar tertentu.
- Tanda dual mengikuti konvensi model Pyomo/HiGHS: dual kendala sumber daya
  `<=` pada model maksimisasi bernilai positif, sedangkan dual kapasitas
  pasokan `<=` pada model minimisasi dapat bernilai negatif.
- Interpretasi harga bayangan finishing sebesar 5 dolar per jam di Latihan
  3.6 dibatasi pada kenaikan RHS 20 jam yang diuji. Penyelesaian ulang pada
  batas tersebut memberi laba 4200.

## Latihan 3.8 secara ringkas

`Simplex LP` cocok untuk objektif dan kendala linear kontinu, memberi optimum
global untuk LP layak dan berbatas, serta menyediakan dual, biaya tereduksi, dan
rentang sensitivitas basis. `GRG Nonlinear` ditujukan untuk model nonlinear
halus, tetapi secara umum hanya menjamin optimum lokal dan dapat bergantung
pada titik awal. `Evolutionary` berguna sebagai heuristik untuk model
tak mulus atau diskret, tanpa jaminan optimum global atau laporan sensitivitas
LP klasik.

Rumus `B2*B3` nonlinear apabila kedua sel merupakan variabel keputusan, jadi
tidak boleh diperlakukan sebagai LP tanpa reformulasi. Contoh
`sqrt(x1)+sqrt(x2)` disebut halus hanya pada domain interior
`x1 >= epsilon`, `x2 >= epsilon`, dengan `epsilon > 0`.

## Menjalankan secara offline

Dari akar lane, buat lingkungan CPython 3.12 sekali pakai dan pasang hanya
dari wheel yang sudah dibekukan:

```powershell
python -m venv <direktori-sementara>
<direktori-sementara>\Scripts\python.exe -m pip install --no-index --find-links=authority/runtime-wheels/windows-cp312-amd64 --require-hashes --only-binary=:all: -r source/o018-open-solver-lab/requirements.lock
<direktori-sementara>\Scripts\python.exe source/o018-open-solver-lab/ch03-spreadsheet-replacements/run_lab.py
<direktori-sementara>\Scripts\python.exe source/o018-open-solver-lab/ch03-spreadsheet-replacements/run_lab.py --check
<direktori-sementara>\Scripts\python.exe -m unittest discover -s source/o018-open-solver-lab/ch03-spreadsheet-replacements -p "test_models.py" -v
```

Tidak diperlukan jaringan, Excel, atau Gurobi. `verification-receipt.json` dan
`verification.log` mencatat instalasi yang dikunci dengan hash, versi runtime,
jumlah uji, hash hasil, dan pemutaran ulang yang identik pada tingkat byte.

## Catatan koreksi terhadap authority

Terjemahan Bab 3/manual yang dibekukan dan lab ini sudah selaras. Keduanya
menerapkan empat ketelitian berikut terhadap authority tanpa mengubah
koefisien model:

1. Authority menyebut nilai `3.1677` pada Latihan 3.3 “exact”; terjemahan dan
   lab memakai `2407651/760055`, kira-kira `3.1677325983`.
2. Sumber Latihan 3.5 menyebut rute “mencapai kapasitas”, walaupun model tidak
   mempunyai kendala kapasitas rute. Terjemahan dan laboratorium tidak membuat
   klaim tersebut.
3. Interpretasi harga bayangan Latihan 3.6 dinyatakan berlaku pada rentang
   kenaikan RHS 20 jam dan diverifikasi dengan penyelesaian ulang di batas itu.
4. Contoh akar kuadrat Latihan 3.8 diberi batas bawah positif secara eksplisit
   agar pernyataan diferensiabilitas tepat.

Hak komponen dan provenance terperinci ada di `ATTRIBUTION.md`. Prosa dan data
adaptasi mengikuti CC BY-SA 4.0; kode Python baru mengikuti Lisensi MIT di
`LICENSE-CODE.txt`.
