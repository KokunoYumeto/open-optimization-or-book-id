# Pemrograman Matematis dan Riset Operasi — Buku 1

**Edisi Bahasa Indonesia (id-ID)**  
*Indonesian edition of Mathematical Programming and Operations Research, Book 1*

Edisi ini menyajikan buku terbuka karya Robert Hildebrand tentang pemrograman
linear, algoritme diskret, dan pemrograman bilangan bulat dalam Bahasa
Indonesia. Struktur matematis, rumus, penomoran, rujukan silang, latihan, dan
hubungan latihan–solusi dipertahankan dari sumber yang dibekukan pada komit
[`1745df89b608899f66983834fa4ec8c8910d18ff`](https://github.com/open-optimization/open-optimization-or-book/tree/1745df89b608899f66983834fa4ec8c8910d18ff).

- [Baca melalui laman edisi](docs/index.html)
- [Buka PDF kanonis](docs/downloads/pemrograman-matematis-dan-riset-operasi-buku-1-id-ID.pdf)
- [Rilis Zenodo dan DOI konsep](https://doi.org/10.5281/zenodo.22059794)
- [Repositori sumber asli](https://github.com/open-optimization/open-optimization-or-book)
- [Pembaca resmi buku asli](https://open-optimization.github.io/open-optimization-or-book/)

> Edisi ini merupakan adaptasi independen. Edisi ini tidak diterbitkan,
> disponsori, atau didukung oleh Robert Hildebrand, Virginia Tech, maupun tim
> Open Optimization.

## Isi repositori

Repositori ini memisahkan dua korpus yang saling terkait tetapi tidak sama:

1. **R017 — Buku 1.** Naskah dan aset edisi Bahasa Indonesia berada di
   `source/Intro-Math-Programming/`. PDF hasil bangun berada di
   `output/book1-pdf/book1-id.pdf`.
2. **O018 — Laboratorium pemecah terbuka.** Pendamping terpisah di
   `source/o018-open-solver-lab/` mengganti jalur praktik yang bergantung pada
   Excel Solver atau Gurobi dengan model yang dapat dijalankan menggunakan
   Pyomo dan HiGHS. Laboratorium tidak mengubah matematika buku dan tidak
   menyatakan dirinya sebagai bagian dari sumber asli.

Lapisan `backend/` menyediakan ID unit dan segmen yang stabil, hierarki,
konsep dan prasyarat, pemetaan istilah, hubungan latihan–solusi, hak komponen,
provenans, koreksi, peristiwa QA, serta ekspor JSON/JSONL/CSV deterministik.
Lapisan ini bersifat tambahan dan netral-lokal agar unit yang sama dapat
digunakan kembali dalam edisi bahasa lain.

## Unduhan rilis

Rilis `2026.08.23-id.5` tersedia melalui
[Zenodo](https://doi.org/10.5281/zenodo.22059794). Salinan byte-identik untuk
laman pembaca statis berada di `docs/downloads/`. Assembler membuat:

- PDF edisi Bahasa Indonesia;
- ZIP sumber LaTeX/TikZ/aset yang diperlukan untuk membangun Buku 1;
- ZIP laboratorium O018 beserta atribusi dan pemberitahuan runtime;
- ZIP backend modular beserta skema, ekspor, dan alat verifikasinya;
- `RELEASE-MANIFEST.json`, `SHA256SUMS.txt`, dan metadata sitasi.

Setiap ZIP memakai urutan entri, metadata, dan waktu tetap. Assembler
membangun ulang ZIP dalam lintasan kedua dan menolak hasil yang tidak identik
byte demi byte. Manifest rilis yang dihasilkan adalah sumber kebenaran untuk
ukuran dan SHA-256 artefak publik.

## Membangun PDF

Prasyarat bangun mengikuti closure yang dibekukan bersama edisi: PowerShell,
MiKTeX/pdfLaTeX, `latexmk`, Biber, MakeIndex, dan MuPDF (`mutool`). Dari akar
repositori:

```powershell
powershell -NoProfile -ExecutionPolicy Bypass -File `
  .\source\Intro-Math-Programming\baseText\book\build-book1-id.ps1
```

Verifikasi struktur PDF, metadata, tautan, outline, tujuan internal, dan font:

```powershell
python .\qa\book1-final-verify.py
```

PDF mempunyai teks Unicode yang dapat diekstrak, teks alternatif/ActualText
pada aset yang didukung, bookmark, dan tautan internal. PDF belum merupakan
PDF bertag dan **tidak** diklaim sesuai PDF/UA. Gunakan HTML pembaca atau
unduh PDF untuk memilih pembaca aksesibel yang paling sesuai.

## Menjalankan laboratorium O018

Runtime yang diterima dibekukan dalam
`source/o018-open-solver-lab/requirements.lock`. Contoh pemasangan daring:

```powershell
python -m venv .venv
.\.venv\Scripts\python -m pip install -r `
  .\source\o018-open-solver-lab\requirements.lock
```

Setiap direktori bab memiliki `README.md`, data, hasil yang diharapkan, kode,
uji, dan receipt verifikasi. Jalankan perintah yang tercantum dalam README bab
tersebut. Hash closure offline Windows/CPython dan pemberitahuan pihak ketiga
dibekukan dalam paket O018; pemberitahuan runtime juga tersedia di
`authority/runtime-licenses/`. Berkas wheel tidak dilacak dalam repositori.

## Membangun dan memeriksa backend

Exporter hanya memakai pustaka standar Python:

```powershell
python .\scripts\export_backend.py --require-bound-targets
python .\scripts\export_backend.py --require-bound-targets --check
```

`backend/input/backend-input.json` adalah sumber data tersunting. Skema berada
di `backend/schema/`; keluaran konsolidasi, JSONL, CSV, dan manifest berada di
`backend/dist/`. Opsi `--check` membuat ulang ekspor dan membandingkan setiap
byte dengan keluaran yang tersimpan.

## Merakit paket rilis

Untuk identitas pembaca final yang dibekukan:

```powershell
python .\release\assemble_release.py `
  --expected-pdf-bytes 26425739 `
  --expected-pdf-sha256 daa9b79df3684729cc204b563669f400866d8fbd12c0977d32ff9897276a7a49
```

Identitas mesin lengkap, termasuk receipt QA yang mengikat PDF 666 halaman
tersebut, berada di `release/reader-identity.json`.

Assembler membaca hanya jalur edisi yang disebutkan secara eksplisit,
menjalankan pemeriksaan backend tertutup-gagal, menolak symlink dan artefak
cache, memvalidasi semua tautan lokal di laman pembaca, lalu menulis receipt
ke `qa/release-package-report.json`.

## Lisensi, atribusi, dan bantuan AI

Teks, terjemahan, dan aset buku yang dapat diadaptasi didistribusikan menurut
[CC BY-SA 4.0](https://creativecommons.org/licenses/by-sa/4.0/). Kode sumber
asli dan alat bangunnya mengikuti lisensi MIT sumber; kode baru O018 dan alat
edisi mengikuti lisensi MIT tersendiri. Prosa/data O018 yang mengadaptasi soal
buku tetap CC BY-SA 4.0. Komponen pihak ketiga mempertahankan lisensinya
masing-masing. Lihat [peta hak komponen](LICENSES/README.md),
[pemberitahuan edisi](NOTICE/EDITION.md), dan atribusi terperinci di dalam
buku.

Terjemahan dan lapisan produksi edisi ini disiapkan dengan bantuan
OpenAI Codex gpt-5.6-sol, Ultra atas permintaan pengguna. AI tidak dicantumkan
sebagai pengarang; Robert
Hildebrand tetap diatribusikan sebagai pengarang buku sumber. Perubahan
semantik dilarang, dan hasil diperiksa melalui bangun deterministik, pemeriksa
struktur, pengujian laboratorium, serta tinjauan visual.

Untuk sitasi, gunakan [`CITATION.cff`](CITATION.cff) dan DOI
[`10.5281/zenodo.22059794`](https://doi.org/10.5281/zenodo.22059794).
