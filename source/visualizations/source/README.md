# Visualisasi Buku 1 — id-ID

Direktori ini memuat dua sumber interaktif yang dilokalkan: tutorial Excel
Solver dan demonstrasi aliran jaringan. Keduanya merupakan bahan pendamping;
PDF Buku 1 tidak bergantung pada runtime JavaScript ini.

Runtime telah dipakukan melalui `package.json` dan `package-lock.json`.

```powershell
npm ci
npm run build
```

Hasil bangun berada di `dist/`. Direktori `dist/` dan `node_modules/` sengaja
tidak disimpan dalam paket sumber karena keduanya dapat dibuat ulang secara
deterministik dari lockfile. Lihat `THIRD_PARTY-NOTICES.md` untuk lisensi
ketergantungan langsung.
