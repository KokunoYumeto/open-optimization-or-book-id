# Pendamping terbuka Bab 15: pemrograman bilangan bulat

Direktori ini adalah laboratorium O018 yang terpisah untuk seluruh 16 latihan
Bab 15, *Pengantar Formulasi Pemrograman Bilangan Bulat*. Laboratorium
mempertahankan data, matematika, label, kelompok kesulitan, dan urutan edisi
Bahasa Indonesia R017, lalu memeriksa hasil numeriknya dengan
Pyomo 6.10.1 dan antarmuka \`appsi_highs\` untuk HiGHS 1.15.1.

## Cakupan

- 16 dari 16 latihan dicakup dengan ID buku stabil \`15.1\` sampai \`15.16\`;
- label LaTeX asli \`ex:knapsack-hiker\` sampai \`ex:flowshop\` disimpan;
- model biner, bilangan bulat, campuran, dan relaksasi LP dibangun ulang tanpa
  Gurobi, Excel, CPLEX, atau pemecah berpemilik;
- jawaban konseptual tetap dicatat dalam Bahasa Indonesia, sedangkan setiap
  pernyataan optimum yang dapat dihitung diperiksa oleh solver atau pencacahan
  lengkap;
- dua kekhasan sumber dipertahankan sebagai provenance: tiga (bukan dua)
  penempatan stasiun optimal pada Latihan 15.3, dan perbedaan antara frasa
  “tepat satu” pada Latihan 15.10 dengan semantik atau-inklusif formulasi
  Big-\(M\) standar;
- dua SVG id-ID yang dapat diakses memperlihatkan pewarnaan graf Latihan 15.9
  dan jadwal flow-shop Latihan 15.16.

\`data.json\` adalah masukan terstruktur dan inventaris sumber.
\`expected-results.json\` adalah orakel independen. \`results.json\` memuat
sertifikat jawaban, catatan solver, pemetaan buku--manual, cacat sumber, dan
inventaris visual. Tidak ada latihan yang belum terselesaikan.

## Menjalankan secara offline

Dari akar lane, gunakan runtime CPython 3.12 yang dikunci:

    <python-terkunci> source/o018-open-solver-lab/ch15-integer-programming/run_lab.py
    <python-terkunci> source/o018-open-solver-lab/ch15-integer-programming/run_lab.py --check
    <python-terkunci> -m unittest discover -s source/o018-open-solver-lab/ch15-integer-programming -p "test_models.py" -v
    <python-terkunci> source/o018-open-solver-lab/ch15-integer-programming/verify_receipt.py --check

Runtime lengkap dibekukan dalam \`../requirements.lock\` dan
\`../runtime-receipt.json\`. Prosa, data adaptasi, orakel, dan SVG mengikuti
CC BY-SA 4.0. Kode Python baru mengikuti Lisensi MIT dalam
\`LICENSE-CODE.txt\`; provenance dan batas hak dijelaskan dalam
\`ATTRIBUTION.md\`.
