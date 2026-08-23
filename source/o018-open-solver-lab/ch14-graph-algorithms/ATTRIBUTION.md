# Atribusi, provenance, dan hak komponen

## Soal, manual, prosa, dan data adaptasi

Laboratorium ini mengadaptasi Bab 14, *Algoritme Graf*, dari *Mathematical
Programming and Operations Research, Book 1*, Robert Hildebrand dkk., pada
komit sumber `1745df89b608899f66983834fa4ec8c8910d18ff`.

Empat saksi hidup yang dibekukan adalah:

- bab otoritas: 153.603 byte, SHA-256
  `3dd0d46fdebb5794dd3597b387fd116cd5c12bcc1320453f0b053c8a3875b2bf`;
- manual otoritas: 20.192 byte, SHA-256
  `6b16c6ca1aac795f83c74fa5f128926b1edbac94b7dc086dc81067df5f6945e8`;
- bab terjemahan Indonesia: 160.224 byte, SHA-256
  `4353255f2fe5ddc304a57e9f38be20d54de2b1d2f365fbb78166a5d33e74482a`;
- manual terjemahan Indonesia: 22.169 byte, SHA-256
  `ce143e1c44694c9d47d00870fc31d1e63c70c1fe9d679e32593bc5eef9b7689a`.

Jalur, peran, ukuran, dan hash yang sama terdapat dalam `data.json`. Uji unit
membaca keempat berkas hidup dan menolak perubahan satu byte pun.

Konten buku dinyatakan CC BY-SA 4.0 dalam `LICENSE-Content` pada komit sumber.
Bab sumber juga menyatakan bahwa sebagian besar materinya, termasuk sejumlah
latihan, diadaptasi dari bab Teori Graf dalam *Math in Society* karya David
Lippman, yang berlisensi CC BY-SA 3.0. Atribusi bertingkat ini dipertahankan;
laboratorium tidak menghapus hak atau kredit sumber terdahulu. Prosa adaptasi,
data, orakel, dan SVG laboratorium mengikuti CC BY-SA 4.0.

`results.json`, resi, dan log adalah keluaran faktual; tidak ada klaim hak
kreatif tambahan atas byte tersebut.

## Batas adaptasi

Laboratorium mempertahankan empat latihan di dalam bab dan 19 butir pada
bagian Latihan sebagai dua lapisan penomoran yang berbeda. Cek pembelajaran
`lc:graph-5cities` disimpan sebagai cek, bukan dinomori ulang sebagai latihan.
Butir Eksplorasi dan dua soal berbasis raster tetap dinilai dengan rubrik.

Empat catatan provenance disimpan tanpa kontak dengan penulis:

1. waktu Bern--Frankfurt `3.55` pada saksi hulu dibaca sebagai `3:55`, sesuai
   solusi terpilih, dan telah dinormalkan pada sumber id-ID;
2. Keterampilan 1--2 memakai raster beresolusi rendah, sehingga perincian yang
   tidak terlihat tidak dipaksakan;
3. gambar Prim tujuh simpul setelah Latihan 14.3 bukan graf enam simpul yang
   ditanyakan latihan tersebut;
4. dua referensi nomor soal diketik manual dan rentan jika urutan berubah.

Catatan ini tidak mengubah matematika soal. `o018_math_correction_count` tetap
nol.

## Kode dan runtime

Kode baru `model.py`, `plot_svg.py`, `run_lab.py`, `test_models.py`, dan
`verify_receipt.py` tersedia menurut Lisensi MIT; lihat `LICENSE-CODE.txt`.
Lisensi ini tidak mengubah lisensi konten buku, data adaptasi, orakel, atau SVG.

Laboratorium memakai CPython 3.12 dan hanya pustaka standar Python. NetworkX
tidak tersedia dalam runtime yang dikunci, sehingga tidak termasuk dalam
closure maupun dinyatakan sebagai pemeriksa. Implementasi Dijkstra,
Bellman--Ford, Kruskal, Prim, enumerasi pohon merentang, BFS, dan Levenshtein
ada di paket ini dan diperiksa silang secara independen di tingkat algoritme.
