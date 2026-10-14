# Sharingan Browser — source awal

Browser Android berbasis Chromium/Kiwi dengan pengelola extension dan import extension ZIP melalui developer mode.

**Status: source eksperimental, belum menjadi APK dan belum pernah dikompilasi.** Paket ini berisi overlay source Kiwi yang dipin, perubahan Sharingan yang sudah terintegrasi, patch terpisah, skrip persiapan/build Linux, workflow GitHub Actions standar, serta extension uji. Ini bukan checkout Chromium lengkap. File-file Chromium yang tidak ada di overlay harus diambil lewat proses checkout.

## Yang sudah ditulis

- Nama launcher **Sharingan Browser**, application ID `com.sharingan.browser`, ikon mata merah orisinal sebagai ikon awal.
- Settings → **Extension developer mode**, memakai preferensi profil Chromium yang sama dengan `chrome://extensions`.
- Menu → **Install extension ZIP** → pemilih dokumen Android → konfirmasi → staging di cache → `ZipFileInstaller` → `UnpackedInstaller`.
- UI dan native memeriksa developer mode. Import dibatasi ke profil reguler; akses incognito dan `file://` tidak otomatis diberikan.
- Copy dokumen berjalan di thread I/O, ukuran ZIP masuk dibatasi 64 MiB, file staging diberi nama acak dan dibuang setelah selesai.
- Hasil ekstraksi disimpan di `SharinganDevExtensions` di dalam profil, bukan cache. Pesan sukses menunggu callback instalasi extension.
- Java, JNI generator, native build target, resource, menu, dan Settings sudah dihubungkan dalam overlay.
- Jalur pengelolaan extension dan instalasi Web Store dari Kiwi dipertahankan. Kompatibilitas aktualnya belum diuji.

Untuk memakai rancangan fitur setelah build: buka tab reguler → Settings → aktifkan Extension developer mode → menu Install extension ZIP → pilih ZIP dengan `manifest.json` di root → Install → kelola lewat menu Extensions. Developer mode bukan Android USB debugging. Mematikannya memblokir import baru; extension yang sudah dipasang harus dinonaktifkan melalui Extensions.

## Temuan yang mengubah isi handoff

Handoff hanya tersedia sebagai Markdown; folder `browser-build/` dan patch lamanya tidak tersedia. Implementasi di paket ini ditulis ulang dari source publik.

Repo pilihan handoff, `EduBolthey/Kiwi-Browser-Revived`, diperiksa pada commit `9806d8c9a2ae8952a1e68b64aedcd225bcd3fbe3`:

1. `CHROMIUM_VERSION` dan `KIWI_VERSION` menyebut 132.0.6834.83, tetapi `VERSION` masih 93.0.4577.21. Ini tanda metadata tidak konsisten, **bukan bukti bahwa engine yang bisa dibangun pasti 93 atau 132**.
2. Workflow `build_kiwi_standalone.yml` mengunduh APK Kiwi yang sudah jadi, mengubah resource/native bytes, kemudian menandatanganinya ulang. Workflow itu **tidak membuktikan source berhasil dikompilasi**.
3. Workflow lama juga mengandalkan layanan build eksternal. Paket ini tidak menyertakan workflow repack, publish, atau endpoint build tersebut.
4. Checklist handoff melewatkan pendaftaran Java pada `generate_jni("chrome_jni_headers")`; perubahan ini sudah disertakan.
5. ZIP installer pada fork memakai variabel global `additional_path` untuk direktori manifest. Patch menghapus state bersama itu dan memulihkan kontrak manifest root. ZIP dengan folder pembungkus ditolak. Ekstraksi tetap menggunakan layanan unzip Chromium.
6. Android Chromium membutuhkan Linux x86-64. Mac dapat dipakai untuk mengedit source dan menjalankan pemeriksaan paket, bukan build APK native.

**Chromium 132 hanya kandidat baseline berdasarkan metadata repo.** Kompatibilitas keseluruhan overlay terhadap checkout 132 belum dibuktikan. Build Linux pertama bisa menemukan pekerjaan porting pada source warisan, bukan hanya error kecil dari patch Sharingan. Versi engine lama ini juga belum layak dinyatakan siap rilis harian tanpa pemeliharaan keamanan.

## Coba build gratis di GitHub Actions

Workflow sudah tersedia di `.github/workflows/android-free.yml`. Gunakan **repo publik**, letakkan isi folder paket di root repo (termasuk `.github`), lalu buka **Actions → Sharingan Android - free runner experiment → Run workflow**.

Pilih `preflight` untuk mengukur ruang setelah cleanup, atau `build` untuk mencoba APK. Default: build arm64 dengan dua worker. [Preflight pertama](https://github.com/wilgooo/sharingan-browser/actions/runs/38576425331) sukses pada 14 Oktober 2026: 18 tes tooling lolos dan ruang disk setelah cleanup 113,85 GiB. Kompilasi Chromium dan APK belum diuji. Instruksi lengkap ada di [GITHUB_ACTIONS_FREE.md](docs/GITHUB_ACTIONS_FREE.md).

## Isi paket

| Path | Isi |
|---|---|
| `chromium-overlay/` | 8.291 file source/resource dari fork yang dipin, termasuk perubahan Sharingan |
| `patches/sharingan.patch` | Perubahan Sharingan terhadap commit fork yang dipin; jangan diterapkan dua kali di atas overlay siap pakai |
| `config/upstream.lock.json` | Asal source, commit, kandidat versi, dan status build |
| `config/overlay.sha256.json` | Hash setiap file overlay untuk pemeriksaan integritas |
| `.github/workflows/android-free.yml` | Workflow manual, repo publik, runner standar, upload log dan APK hasil build |
| `config/args.free.gn` | Konfigurasi CI hemat resource; tanpa debug symbols/ThinLTO, satu linker |
| `config/args.gn` | Konfigurasi awal Android arm64, package Sharingan, API credentials kosong |
| `scripts/` | Fetch, persiapan overlay, build Linux, pemeriksaan paket, pembuat fixture |
| `examples/hello-sharingan/` | Extension MV3: content script, service worker, popup |
| `examples/zips/` | Satu ZIP positif dan enam fixture negatif |
| `docs/BUILD_LINUX.md` | Cara melanjutkan di builder Linux |
| `docs/TEST_PLAN.md` | Verifikasi perangkat dan kasus gagal |
| `docs/VALIDATION.md` | Hasil pemeriksaan yang benar-benar dijalankan |

## Pemeriksaan yang bisa dijalankan di Mac

Dari folder paket ini, dengan Python 3.9+ dan Node.js:

```bash
python3 scripts/verify_source.py
python3 -B -m unittest discover -s tests -v
bash -n scripts/fetch_chromium.sh
bash -n scripts/build_linux.sh
node --check examples/hello-sharingan/content.js
```

Pemeriksaan ini tidak menggantikan kompilasi Java/C++, GN, instalasi APK, atau pengujian browser.

## Batas source awal

- Belum ada hasil build atau pengujian Android; dukungan MV2/MV3 dan Chrome Web Store belum dibuktikan melalui runtime.
- Branding baru mencakup identitas launcher/package/ikon. Beberapa halaman bawaan, teks, dan tautan warisan Kiwi masih perlu dibersihkan.
- Import ulang ZIP tanpa `key` manifest dapat menghasilkan ID berbeda karena path ekstraksi berbeda. Untuk update dengan ID stabil, extension perlu key publik stabil dan pengujian update tersendiri.
- Remove menonaktifkan/menghapus registrasi melalui pengelola bawaan; garbage collection folder developer yang sudah tidak dipakai belum ditambahkan. Folder gagal dibersihkan pada jalur callback normal, tetapi penghentian proses di tengah install dapat meninggalkan file sementara.
- Batas 64 MiB hanya membatasi input ZIP terkompresi. Kuota ukuran hasil ekstraksi dan penanganan ZIP bomb belum ditambahkan.
- Ini development build; release signing, update APK, store publishing, dan audit semua perilaku warisan belum dikerjakan.

## Sumber

- [Kiwi-Browser-Revived, commit yang dipin](https://github.com/EduBolthey/Kiwi-Browser-Revived/tree/9806d8c9a2ae8952a1e68b64aedcd225bcd3fbe3)
- [Workflow repack yang diperiksa](https://github.com/EduBolthey/Kiwi-Browser-Revived/blob/9806d8c9a2ae8952a1e68b64aedcd225bcd3fbe3/.github/workflows/build_kiwi_standalone.yml)
- [Dokumentasi build Android Chromium](https://chromium.googlesource.com/chromium/src/+/main/docs/android_build_instructions.md)

Tidak ada biner, source tertutup, atau aset Lemur yang disalin. Lisensi dan atribusi upstream dipertahankan; lihat `LICENSE`, `UPSTREAM_LICENSE`, serta pemberitahuan dalam source.
