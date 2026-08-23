# Pendamping terbuka Bab 14: algoritme graf

Direktori ini adalah laboratorium O018 terpisah untuk Bab 14, *Algoritme
Graf*. Laboratorium mempertahankan data, matematika, label, dan struktur
berlapis edisi Bahasa Indonesia R017, lalu menyediakan implementasi Python
terbuka yang dapat dijalankan tanpa jaringan.

## Cakupan

- 23 dari 23 butir tercakup: Latihan 14.1--14.4, Keterampilan 1--14,
  Konsep 15--17, dan Eksplorasi 18--19;
- cek pembelajaran `lc:graph-5cities` disimpan terpisah agar tidak keliru
  dihitung sebagai latihan kelima;
- Dijkstra diperiksa silang dengan Bellman--Ford pada seluruh kasus numerik;
- Kruskal diperiksa silang dengan enumerasi semua pohon merentang yang layak,
  dan Prim diperiksa silang dengan Kruskal;
- derajat, lema jabat tangan, komponen terhubung, semua lintasan terpendek
  tanpa bobot, dan jarak Levenshtein dihitung secara deterministik;
- dua SVG id-ID yang dapat diakses memperlihatkan pohon merentang minimum
  Latihan 14.1 dan lintasan terpendek Latihan 14.4;
- butir yang sengaja terbuka atau bergantung pada gambar tetap berstatus
  rubrik; laboratorium tidak mengarang satu jawaban tunggal.

Runtime terkunci tidak memuat NetworkX. Karena itu, contoh NetworkX pada buku
digantikan oleh implementasi pustaka standar Python dengan hasil matematis
yang sama. Tidak ada pemecah berpemilik, paket graf pihak ketiga, atau akses
jaringan.

`expected-results.json` adalah orakel independen yang ditulis terpisah dari
mesin. `results.json` menyimpan sertifikat setiap butir, jejak algoritme,
pemeriksaan silang, provenance, catatan sumber, dan inventaris visual.

## Menjalankan secara offline

Dari akar lane, gunakan runtime CPython 3.12 yang dikunci:

```powershell
<python-terkunci> source/o018-open-solver-lab/ch14-graph-algorithms/run_lab.py --check
<python-terkunci> -m unittest discover -s source/o018-open-solver-lab/ch14-graph-algorithms -p "test_models.py" -v
<python-terkunci> source/o018-open-solver-lab/ch14-graph-algorithms/verify_receipt.py --check
```

Untuk regenerasi terkontrol, gunakan `run_lab.py --write`, lalu ulangi seluruh
pemeriksaan. Prosa, data adaptasi, orakel, dan SVG mengikuti CC BY-SA 4.0.
Kode Python baru mengikuti Lisensi MIT dalam `LICENSE-CODE.txt`; batas hak dan
provenance dijelaskan dalam `ATTRIBUTION.md`.
