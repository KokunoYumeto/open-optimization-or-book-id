# Atribusi, provenance, dan hak komponen

## Soal, manual, prosa, dan data adaptasi

Laboratorium ini mengadaptasi sembilan latihan Bab 12, *Perangkat Lunak --
Python*, dari *Mathematical Programming and Operations Research, Book 1*,
Robert Hildebrand dkk., pada komit sumber
`1745df89b608899f66983834fa4ec8c8910d18ff`.

Empat saksi hidup yang dibekukan adalah:

- bab otoritas: 54.729 byte, SHA-256
  `3570d7199cb26850ae22523c6506324b51685f05ac48969476356b6660bad951`;
- manual otoritas: 20.228 byte, SHA-256
  `5ff803126798622edd790e3ad6f962102bbb369f04d355bcd1e5d982855ec905`;
- bab terjemahan Indonesia: 57.622 byte, SHA-256
  `ecadcf255ec67e9ee538735255268bb7142bdd8511dd1dccdfa0a9aeeeae5801`;
- manual terjemahan Indonesia: 21.520 byte, SHA-256
  `73fed9c588d36a0915c0777e7f118330d18aa71b10229fac19e0c7e830820246`.

Jalur, peran, ukuran, dan hash yang sama terdapat dalam `data.json`. Uji unit
membaca keempat berkas hidup dan menolak perubahan satu byte pun.

Konten buku dinyatakan CC BY-SA 4.0 dalam `LICENSE-Content` pada komit sumber.
Prosa adaptasi, data, dan orakel laboratorium mengikuti CC BY-SA 4.0.
`results.json`, resi, dan log adalah keluaran faktual; tidak ada klaim hak
kreatif tambahan atas byte tersebut.

## Batas adaptasi

Bab sumber memakai PuLP dan CBC. Laboratorium terpisah ini tidak mengganti bab,
tidak mengubah koefisien, arah tujuan, ruas kanan, urutan latihan, label, atau
jawaban matematisnya. Adaptasi hanya memetakan konstruksi pemodelan ke Pyomo dan
menjalankannya dengan HiGHS melalui antarmuka `appsi_highs`.

Semua latihan buku 12.1--12.9 selaras dengan entri manual 12.1--12.9. Dalam
closure yang dibekukan tidak ditemukan cacat sumber baru yang perlu dicatat,
dan laboratorium tidak membuat koreksi matematika baru. Latihan 12.7 tetap
membedakan dua kasus sumber: kendala tenaga kerja yang hilang dan ekspresi
tanpa operator perbandingan yang menimpa tujuan dalam PuLP. Pyomo tidak
dipaksa meniru API PuLP; kedua model salah itu dibangun secara eksplisit agar
dampak matematisnya dapat dibandingkan dan diuji.

## Kode dan runtime pihak ketiga

Kode baru `model.py`, `run_lab.py`, `test_models.py`, dan `verify_receipt.py`
tersedia menurut Lisensi MIT; lihat `LICENSE-CODE.txt`. Lisensi ini tidak
mengubah lisensi konten buku, data adaptasi, atau orakel.

- Pyomo 6.10.1 — BSD-3-Clause;
- highspy/HiGHS 1.15.1 — MIT untuk paket standar tanpa ekstra HiPO;
- NumPy 2.5.2 — `BSD-3-Clause AND 0BSD AND MIT AND Zlib AND CC0-1.0`.

Versi dan hash wheel dikunci dalam `../requirements.lock`; bukti lisensi dan
manifest wheel berada di `authority/runtime-licenses/` dan
`authority/runtime-wheels/`.
