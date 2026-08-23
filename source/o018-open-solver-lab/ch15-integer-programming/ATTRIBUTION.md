# Atribusi, provenance, catatan sumber, dan hak komponen

## Soal, manual, prosa, dan data adaptasi

Laboratorium ini mengadaptasi semua 16 latihan Bab 15, *Pengantar Formulasi
Pemrograman Bilangan Bulat*, dari *Mathematical Programming and Operations
Research, Book 1*, Robert Hildebrand dkk., pada komit sumber
\`1745df89b608899f66983834fa4ec8c8910d18ff\`.

Empat saksi hidup yang dibekukan adalah:

- bab otoritas: 123.631 byte, SHA-256
  \`1c3ca88201b3ae0a71d08f383611cd2e939700fda44414168447acf8139e4d22\`;
- manual otoritas: 18.773 byte, SHA-256
  \`bffcfe89eafd124d42db814d9cce93eac662bd513104e5c8fd9b738c912af081\`;
- bab terjemahan Indonesia: 136.692 byte, SHA-256
  \`d5d12875d4841ef4ded4a4d2cf69311070cd9d59a5a1fd34c333ead8f1a26653\`;
- manual terjemahan Indonesia: 20.710 byte, SHA-256
  \`85d3a2960c32933717ac172a590085eb510689cc73ab1ec10420ffe2af31e0af\`.

Jalur, peran, ukuran, dan hash yang sama terdapat dalam \`data.json\`. Uji unit
membaca keempat berkas hidup dan menolak perubahan satu byte pun.

Konten buku dinyatakan CC BY-SA 4.0 dalam \`LICENSE-Content\` pada komit sumber.
Prosa adaptasi, data, orakel, dan SVG laboratorium mengikuti CC BY-SA 4.0.
\`results.json\`, resi, dan log adalah keluaran faktual; tidak ada klaim hak
kreatif tambahan atas byte tersebut.

## Pemetaan buku--manual dan catatan yang tidak disamarkan

Bab dan manual sama-sama memuat 16 latihan dan selaras satu-ke-satu. Dua
catatan berkeyakinan tinggi tetap tampak:

1. \`DEF-CH15-FIRE-PLACEMENTS\`: pencacahan keenam distrik membuktikan tepat
   tiga pasangan optimal pada Latihan 15.3:
   \(\{2,5\}\), \(\{3,4\}\), dan \(\{1,6\}\). Catatan manual menjelaskan bahwa
   solusi terpilih buku dahulu hanya mencantumkan dua pasangan; saksi yang
   dibekukan kini telah memuat pasangan ketiga.
2. \`DEF-CH15-EITHER-OR-SEMANTICS\`: Latihan 15.10 mengatakan “tepat satu”
   kendala harus berlaku. Formulasi Big-\(M\) yang diminta hanya memilih
   kendala yang wajib diterapkan dan membolehkan titik yang memenuhi keduanya,
   sehingga semantiknya “setidaknya satu”. Manual juga menandai hal ini.

Laboratorium tidak mengubah teks buku dan tidak menghubungi penulis.

## Kode dan runtime pihak ketiga

Kode baru \`model.py\`, \`plot_svg.py\`, \`run_lab.py\`,
\`test_models.py\`, dan \`verify_receipt.py\` tersedia menurut Lisensi MIT;
lihat \`LICENSE-CODE.txt\`. Lisensi ini tidak mengubah lisensi konten buku,
data adaptasi, orakel, atau SVG.

- Pyomo 6.10.1 — BSD-3-Clause;
- highspy/HiGHS 1.15.1 — MIT untuk paket standar tanpa ekstra HiPO;
- NumPy 2.5.2 — \`BSD-3-Clause AND 0BSD AND MIT AND Zlib AND CC0-1.0\`.

Versi dan hash wheel dikunci dalam \`../requirements.lock\`; bukti lisensi dan
manifest wheel berada di \`authority/runtime-licenses/\` dan
\`authority/runtime-wheels/\`. Perender SVG hanya memakai pustaka standar
Python dan termasuk kode MIT paket ini.
