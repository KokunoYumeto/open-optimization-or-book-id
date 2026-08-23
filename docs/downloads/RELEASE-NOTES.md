# Pemrograman Matematis dan Riset Operasi — Buku 1

## Edisi Bahasa Indonesia · 2026.08.23-id.5

Rilis ini menyediakan edisi Bahasa Indonesia (`id-ID`) lengkap dari
*Mathematical Programming and Operations Research, Book 1* karya Robert
Hildebrand. Edisi diturunkan dari komit sumber
`1745df89b608899f66983834fa4ec8c8910d18ff` dan mempertahankan struktur,
matematika, rumus, penomoran, rujukan silang, latihan, dan hubungan
latihan–solusi.

### Isi rilis

- PDF Buku 1 yang dapat dicari, dengan bookmark dan tautan internal;
- sumber LaTeX/TikZ, bibliografi, aset, dan alat bangun;
- laboratorium O018 berbasis Pyomo+HiGHS sebagai pendamping terpisah;
- backend modular dengan ID stabil serta ekspor JSON/JSONL/CSV;
- manifest JSON, SHA-256, metadata sitasi, atribusi, dan peta lisensi.

Versi `id.5` mempertahankan QA terminologi bidang Bahasa Indonesia yang
terikat-hash dari `id.3`, termasuk koreksi `solusi layak dasar` menjadi istilah
kanonis `solusi basis layak`, lalu membangun ulang PDF dengan penekanan metadata
PTEX agar jalur absolut mesin pembangun tidak ikut terbit. Matematika, urutan,
dan cakupan instruksional tidak berubah dari `id.4`. Selain itu, paket sumber
dan backend memuat receipt QA yang diperbarui agar seluruh identitas internal
sejalan dengan pembaca id.5.

O018 menyediakan jalur komputasi bebas dan terbuka tanpa mengubah matematika
buku. Ia tidak menyatakan bahwa sumber asli memakai Pyomo/HiGHS dan tidak
mengganti ketergantungan Excel/Gurobi di sumber secara diam-diam. Buku 2 yang
belum selesai berada di luar cakupan rilis ini.

### Aksesibilitas

PDF memuat teks Unicode, ActualText/teks alternatif pada aset yang didukung,
bookmark, dan tautan. PDF belum bertag dan tidak diklaim sesuai PDF/UA. Laman
pembaca statis responsif disertakan dalam paket sumber; penerbitan GitHub Pages
adalah saluran terpisah dan tidak diklaim oleh rilis Zenodo ini.

### Hak dan atribusi

Konten dan terjemahan buku mengikuti CC BY-SA 4.0. Kode sumber asli dan kode
baru memiliki lisensi MIT terpisah; komponen runtime mempertahankan lisensinya
sendiri. Edisi ini independen dan tidak menyiratkan dukungan dari Robert
Hildebrand, Virginia Tech, atau Open Optimization.

Terjemahan dan lapisan produksi disiapkan dengan bantuan
OpenAI Codex gpt-5.6-sol, Ultra atas permintaan pengguna. AI tidak dicantumkan
sebagai pengarang.

Verifikasi byte unduhan terhadap `SHA256SUMS.txt` atau
`RELEASE-MANIFEST.json`.

### Identitas pembaca kanonis

- Halaman: 666
- Ukuran: 26.425.739 byte
- SHA-256 PDF: `daa9b79df3684729cc204b563669f400866d8fbd12c0977d32ff9897276a7a49`
- SHA-256 receipt QA: `d914ab157350571779a9e4bca62a1b02031560ccda19f00b08c4d61fda5b15b0`

Receipt QA membuktikan bahasa `id-ID`, seluruh font tertanam dan memiliki
pemetaan Unicode, tidak ada font Type 3, dan tidak ada tautan invalid. Status
aksesibilitas tetap dinyatakan secara konservatif: PDF belum bertag dan tidak
diklaim sesuai PDF/UA.
