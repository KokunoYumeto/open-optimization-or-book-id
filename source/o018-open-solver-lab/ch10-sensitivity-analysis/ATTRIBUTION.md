# Atribusi, provenance, koreksi, dan hak komponen

## Soal, manual, prosa, dan data adaptasi

Laboratorium ini mengadaptasi 12 latihan Bab 10, *Analisis Sensitivitas*, dari
*Mathematical Programming and Operations Research, Book 1*, Robert Hildebrand
dkk., pada komit sumber
`1745df89b608899f66983834fa4ec8c8910d18ff`.

Empat saksi hidup yang dibekukan adalah:

- bab authority: 49.842 byte, SHA-256
  `5a112881cdab43e0509ef39ea48656f45f7228488ef8af9ce1fdba2f3d8fbfc5`;
- manual authority: 20.937 byte, SHA-256
  `b0c7bbfca422954e1593b71ec4b55cbed40c918fc4a3d4058cbe24fdf9561597`;
- bab terjemahan Indonesia: 52.340 byte, SHA-256
  `27125508e85609361382af200e24d33d5f979cb68f78c5eee94c06acd6a9c64c`;
- manual terjemahan Indonesia: 22.264 byte, SHA-256
  `6abe9524a7052068e1d5931356d43f24ec5fde441af4080a347124e1088b6ca5`.

Path, peran, ukuran, dan hash yang sama terdapat dalam `data.json`. Uji unit
membaca keempat berkas hidup dan menolak perubahan satu byte pun.

Konten buku dinyatakan CC BY-SA 4.0 dalam `LICENSE-Content` pada komit sumber.
Prosa adaptasi, data, oracle, dan SVG laboratorium mengikuti CC BY-SA 4.0.
`results.json`, receipt, dan log adalah keluaran faktual; tidak ada klaim hak
kreatif tambahan atas byte tersebut.

## Tiga koreksi target yang dipertahankan

Laboratorium tidak membuat koreksi matematis O018 baru. Ia mempertahankan tiga
koreksi berkeyakinan tinggi yang sudah dinyatakan terbuka dalam R017:

1. `CORR-CH10-RHS-B1-SLACK`: sumber menyederhanakan substitusi slack kendala
   pertama menjadi \(x+y+s_1'=9\), padahal persamaan terusiknya tetap memiliki
   ruas kanan \(9+\Delta\). Target mempertahankan hubungan koordinat
   \(s_1=s_1'-\Delta\) tanpa penyederhanaan yang tidak sah.
2. `CORR-CH10-RHS-B3-SLACK`: cacat yang sama muncul untuk kendala ketiga;
   target mempertahankan \(x+2y+s_3'=14+\Delta\) dan
   \(s_3=s_3'-\Delta\).
3. `CORR-CH10-MATRIX-AN-SIGNS`: dalam bentuk
   \(\mathbf{x}_B=\mathbf{b}'-A_N'\mathbf{x}_N\), tanda matriks sumber
   berlawanan dengan kamus akhir. Target memakai
   \(A_N'=\left[\begin{smallmatrix}2&-1\\-1&1\\-3&1\end{smallmatrix}\right]\),
   yang diverifikasi langsung sebagai \(A_B^{-1}A_N\).

Laboratorium menyimpan ID, lokasi sumber/target, dan sertifikat aljabar ketiga
koreksi dalam `data.json` dan `results.json`. Tidak ada percakapan atau kontak
dengan penulis yang dilakukan.

## Batas data Latihan 10.7

Laporan sensitivitas pada Latihan 10.7 memberi nilai variabel, koefisien
objektif, harga bayangan, ruas kanan, serta kenaikan/penurunan yang diizinkan.
Ia tidak memberi matriks koefisien kendala. Karena banyak PL dapat menghasilkan
ringkasan tersebut, laboratorium hanya memeriksa aritmetika dan implikasi lokal
laporan; tidak ada model Pyomo yang direka untuk latihan itu.

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

