# Peta lisensi dan hak komponen

Dokumen ini merangkum hak komponen rilis. Berkas sumber dan bagian **Sumber
dan Atribusi** di dalam buku tetap menjadi catatan yang lebih rinci. Ringkasan
ini bukan nasihat hukum dan tidak mengganti teks lisensi yang berlaku.

| Komponen | Cakupan | Lisensi / status |
|---|---|---|
| R017: prosa, terjemahan, diagram, dan aset buku | `source/Intro-Math-Programming/` dan PDF | CC BY-SA 4.0, dengan atribusi komponen sumber |
| Kode dan alat bangun sumber asli | kode pada corpus R017 | MIT, hak cipta sumber dipertahankan |
| O018: prosa dan data yang mengadaptasi soal buku | `source/o018-open-solver-lab/` | CC BY-SA 4.0 |
| O018: kode laboratorium baru | berkas kode O018 | MIT, Copyright (c) 2026 Indonesian derivative contributors |
| Alat backend dan rilis baru | `scripts/`, `release/` | MIT, Copyright (c) 2026 Indonesian derivative contributors |
| Pyomo 6.10.1 | runtime O018 | BSD-3-Clause |
| highspy/HiGHS 1.15.1 standar | runtime O018 | MIT, beserta pemberitahuan komponen yang dibundel |
| NumPy 2.5.2 | runtime O018 | ekspresi komponen `BSD-3-Clause AND 0BSD AND MIT AND Zlib AND CC0-1.0` |
| React, React DOM, KaTeX, Lucide React, Vite | sumber visualisasi pendamping | MIT dan ISC; versi dipakukan dalam lockfile dan dirinci dalam pemberitahuan visualisasi |

Teks hukum CC BY-SA 4.0 tersedia pada
<https://creativecommons.org/licenses/by-sa/4.0/legalcode>. Pemberitahuan MIT
untuk kode baru ada di [`MIT-NEW-CODE.txt`](MIT-NEW-CODE.txt); pemberitahuan
kode sumber asli ada di [`MIT-UPSTREAM-CODE.txt`](MIT-UPSTREAM-CODE.txt).
Assembler juga memasukkan salinan `LICENSE-Content` dan `LICENSE-Code` dari
komit sumber yang dibekukan ke setiap paket yang relevan.

Materi yang diadaptasi oleh buku mencakup komponen CC BY 4.0, CC BY 3.0 US,
CC BY 2.0, CC BY-SA 4.0, CC BY-SA 3.0 US, CC BY-SA 2.5, dan domain publik. Nama pengarang, asal,
mekanisme kompatibilitas, serta penggunaan setiap komponen dicatat pada bab
**Sumber dan Atribusi** di PDF dan
`source/Intro-Math-Programming/baseText/book/frontmatter/sources-attribution.tex`.

Merek dagang, hak paten, dan hak lain yang tidak diberikan oleh lisensi
tersebut tidak dilisensikan. Tidak ada dukungan dari pengarang atau proyek
sumber yang boleh disiratkan.
