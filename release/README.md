# Perakitan rilis

`assemble_release.py` merakit artefak publik setelah PDF kanonis dan backend
modular dibekukan. Skrip ini tidak memakai Git, tidak membaca token, dan tidak
menerbitkan apa pun. Publikasi GitHub/Pages/Zenodo adalah transaksi terpisah
yang harus memakai byte hasil assembler ini.

Jalankan dari akar edisi dengan identitas PDF final yang dibekukan:

```powershell
python .\release\assemble_release.py `
  --expected-pdf-bytes 26425739 `
  --expected-pdf-sha256 daa9b79df3684729cc204b563669f400866d8fbd12c0977d32ff9897276a7a49
```

`reader-identity.json` mengikat PDF 666 halaman (26.425.739 byte,
SHA-256 `daa9b79df3684729cc204b563669f400866d8fbd12c0977d32ff9897276a7a49`)
ke receipt QA 30.770 byte dengan SHA-256
`d914ab157350571779a9e4bca62a1b02031560ccda19f00b08c4d61fda5b15b0`.

Skrip gagal tertutup jika identitas PDF atau receipt QA tidak cocok, backend
tidak dapat dibuat ulang secara deterministik, ada symlink/junction, ada jalur
yang keluar dari lane, atau direktori keluaran memuat berkas yang tidak
dikenal. Cache Python/LaTeX tidak dimasukkan ke paket.

Artefak dibangun dua kali dengan waktu tetap `2026-08-23T00:00:00Z`, lalu
dibandingkan byte demi byte. Hasil final berada di `release/out/`; hardlink
(atau salinan bila hardlink tidak tersedia) untuk laman pembaca statis berada
di `docs/downloads/`. Receipt lokal berada di
`qa/release-package-report.json`.

`RELEASE-MANIFEST.json` mencatat identitas sumber, peran korpus, hak,
aksesibilitas, ukuran, dan SHA-256 artefak utama. `SHA256SUMS.txt` mencakup
seluruh payload dan metadata pendukung tanpa hash yang bersifat
self-referential.
