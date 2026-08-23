# Atribusi, provenance, koreksi, dan hak komponen

## Soal, manual, prosa, dan data adaptasi

Laboratorium ini mengadaptasi 17 latihan Bab 11, *Dualitas*, dari
*Mathematical Programming and Operations Research, Book 1*, Robert Hildebrand
dkk., pada komit sumber
`1745df89b608899f66983834fa4ec8c8910d18ff`.

Enam saksi hidup yang dibekukan adalah:

- bab dualitas authority: 52.217 byte, SHA-256
  `627b34388b3ce2a3058298c4beb8e76f7c621ae435c8de1b12aca8bc9648f685`;
- bab kelonggaran komplementer authority: 26.931 byte, SHA-256
  `4623cc1ac31689d782f57714bc6778ddc5bae655f30f6b70d88764a20dd4d8f8`;
- manual authority: 31.219 byte, SHA-256
  `a813d9dbfbd735dcea4747c15042b7e25eb58d06cfca2dda29cd6a4b7c3f0249`;
- bab dualitas terjemahan Indonesia: 54.574 byte, SHA-256
  `ce71b6225b7c96fd52bb9c5df2718d6a2355a0482c4aec4350b0b1f0d5d34ec1`;
- bab kelonggaran komplementer terjemahan Indonesia: 28.658 byte,
  SHA-256 `acf99fe82812fc9ad487bdeb4d8a4e2e46918e0e40bb48edcd1a75d075ebc69a`;
- manual terjemahan Indonesia: 34.607 byte, SHA-256
  `6688bdb15e34fba8f412815979df92494ff9018d15f4c8b8661e0ada9b607d2d`.

Path, peran, ukuran, dan hash yang sama terdapat dalam `data.json`. Uji unit
membaca keenam berkas hidup dan menolak perubahan satu byte pun.

Konten buku dinyatakan CC BY-SA 4.0 dalam `LICENSE-Content` pada komit sumber.
Prosa adaptasi, data, oracle, dan SVG laboratorium mengikuti CC BY-SA 4.0.
`results.json`, receipt, dan log adalah keluaran faktual; tidak ada klaim hak
kreatif tambahan atas byte tersebut.

## Tiga koreksi sumber yang dipertahankan

Laboratorium tidak membuat koreksi matematis O018 baru. Ia mempertahankan tiga
koreksi berkeyakinan tinggi yang sudah dinyatakan terbuka dalam R017:

1. `CORR-CH11-CASE2-GEQ`: bentuk simetris kasus minimisasi memakai kendala
   primal `>=` dan kendala dual `<=`. Bentuk lama dengan primal `<=` melanggar
   dualitas lemah; contoh satu variabel memberi nilai primal 0 dan nilai dual
   3. Bentuk terkoreksi memberi nilai 3 pada kedua sisi.
2. `CORR-CH11-MIXED-SIGNS-FREE`: pada contoh “Masalah Dual yang Rumit”,
   kendala primal `>=` dalam maksimisasi memberi `y2 <= 0`, kendala `<=`
   memberi `y3 >= 0`, dan variabel primal bebas memberi persamaan dual.
   Primal contoh itu taklayak dan dual terkoreksi takterbatas, sebagaimana
   diverifikasi langsung oleh HiGHS.
3. `CORR-CH11-EX11-13-CANDIDATE`: Latihan 11.13 menyebut `(1,1)` sebagai
   *kandidat* solusi dual, bukan solusi dual. Kandidat itu melanggar kendala
   pertama (`3 < 5`), sedangkan pasangan optimum sebenarnya bernilai 23.

ID, lokasi, dan sertifikat ketiga koreksi disimpan dalam `data.json` dan
`results.json`. Tidak ada percakapan atau kontak dengan penulis yang dilakukan.

## Cacat hulu berkeyakinan tinggi yang tidak diubah

`UPSTREAM-DEFECT-CH11-STRONG-DUALITY-OMITS-BOTH-INFEASIBLE` mencatat bahwa
teorema yang mengaku mencirikan hubungan primal--dual “secara lengkap” hanya
mendaftar tiga kasus, padahal primal dan dual dapat sama-sama taklayak.
Latihan 11.8 sendiri memberi contoh tegas: penjumlahan dua kendala primal
menghasilkan `0 <= -2`, sedangkan penjumlahan dua kendala dual menghasilkan
`0 >= 2`. Laboratorium melaporkan cacat ini tanpa mengubah saksi sumber.

`UPSTREAM-DEFECT-CH11-EX11-17-RETAIL-REDUNDANT` mencatat bahwa kendala retail
Latihan 11.17 tidak mungkin aktif. Persamaan material memberi
`6x1+9x2+8x3 = 360+2x3 >= 360`, sehingga syarat `>= 80` selalu terpenuhi dan
variabel dual bertanda nonpositif yang dimaksudkan untuk melatih bentuk
campuran menjadi ekonomis vakum. Nilai pengganti yang dimaksud tidak ditebak.

## Kode dan runtime pihak ketiga

Kode baru `model.py`, `plot_svg.py`, `run_lab.py`, `test_models.py`, dan
`verify_receipt.py` tersedia menurut Lisensi MIT; lihat `LICENSE-CODE.txt`.
Lisensi ini tidak mengubah lisensi konten buku, data adaptasi, oracle, atau SVG.

- Pyomo 6.10.1 — BSD-3-Clause;
- highspy/HiGHS 1.15.1 — MIT untuk paket standar tanpa ekstra HiPO;
- NumPy 2.5.2 — `BSD-3-Clause AND 0BSD AND MIT AND Zlib AND CC0-1.0`.

Versi dan hash wheel dikunci dalam `../requirements.lock`; bukti lisensi dan
manifest wheel berada di `authority/runtime-licenses/` dan
`authority/runtime-wheels/`. Renderer SVG memakai hanya pustaka standar Python
dan termasuk kode MIT paket ini.
