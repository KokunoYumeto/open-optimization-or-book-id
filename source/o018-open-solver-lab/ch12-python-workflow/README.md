# Pendamping terbuka Bab 12: alur kerja Python

Direktori ini menyediakan laboratorium O018 yang terpisah untuk seluruh sembilan
latihan Bab 12, *Perangkat Lunak -- Python*. Buku tetap mengajarkan PuLP; lab
ini mempertahankan model, data, tujuan, dan pertanyaan matematis yang sama,
tetapi menjalankannya melalui Pyomo 6.10.1 dan pemecah terbuka HiGHS 1.15.1.
Tidak ada perubahan diam-diam pada bab R017 dan tidak ada pemecah berpemilik.

## Alur kerja enam langkah

Pola yang dipakai berulang kali dalam `model.py` adalah:

1. baca data terstruktur dari `data.json`;
2. buat `ConcreteModel` dan himpunan indeks yang berurutan;
3. nyatakan `Var` beserta domainnya;
4. nyatakan tepat satu `Objective` serta semua `Constraint`;
5. panggil `SolverFactory("appsi_highs")`, matikan keluaran nondeterministik,
   dan tuntut terminasi `optimal`;
6. ekstrak solusi, nilai tujuan, slack, dual, dan pemeriksaan kelayakan.

Langkah keenam bukan hiasan. Setiap pemanggilan solver menyimpan status,
terminasi, varian model, tujuan pemeriksaan, dan pelanggaran maksimum. Untuk
latihan diagnosis, lab juga menghitung kembali laba sebenarnya dan penggunaan
sumber daya; status `optimal` saja tidak dianggap bukti bahwa model yang
dimaksud telah dibangun.

## Cakupan

- 9 dari 9 latihan dicakup dengan ID buku stabil `12.1` sampai `12.9`;
- seluruh label LaTeX (`ex:pulp-new-profit` sampai `ex:pulp-rhs-sweep`) serta
  pemetaan manual 12.1--12.9 dipertahankan;
- 25 pemanggilan Pyomo+HiGHS per regenerasi memeriksa perubahan parameter,
  dua model transportasi, dual dan slack, sapuan kendala epsilon, dua kutu
  pemodelan, tiga arah tujuan, serta sepuluh nilai ruas kanan tenaga kerja;
- semua 25 terminasi harus optimal dan pelanggaran solver maksimum harus nol;
- `expected-results.json` adalah orakel independen, sedangkan `results.json`
  adalah keluaran mesin yang diregenerasi secara deterministik;
- tidak ada latihan yang belum terselesaikan, koreksi matematika O018, atau
  cacat sumber baru yang dicatat untuk bab ini.

## Menjalankan secara offline

Dari akar lane, gunakan runtime CPython 3.12 yang dikunci:

```powershell
<python-terkunci> source/o018-open-solver-lab/ch12-python-workflow/run_lab.py
<python-terkunci> source/o018-open-solver-lab/ch12-python-workflow/run_lab.py --check
<python-terkunci> -m unittest discover -s source/o018-open-solver-lab/ch12-python-workflow -p "test_models.py" -v
<python-terkunci> source/o018-open-solver-lab/ch12-python-workflow/verify_receipt.py --check
```

Runtime lengkap dibekukan dalam `../requirements.lock` dan
`../runtime-receipt.json`. Seluruh langkah berjalan tanpa jaringan, Microsoft
Excel, Gurobi, CPLEX, PuLP, atau pemecah berpemilik lain.

Prosa dan data adaptasi mengikuti CC BY-SA 4.0. Kode Python baru mengikuti
Lisensi MIT dalam `LICENSE-CODE.txt`; batas hak dan provenance dijelaskan dalam
`ATTRIBUTION.md`.
