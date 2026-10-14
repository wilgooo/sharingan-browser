# Pengujian perangkat — belum dijalankan

Gunakan Android arm64 dengan profil uji. Catat versi OS, perangkat, commit source, SHA-256 APK, sertifikat, dan hasil GN/build. Smoke test tidak membuktikan kompatibilitas semua extension Chrome.

| Langkah | Hasil yang wajib diperiksa |
|---|---|
| Fresh install dan buka aplikasi | Nama Sharingan Browser, package `com.sharingan.browser`, ikon baru; browsing dasar bekerja |
| Buka Settings lalu Extensions | Developer mode OFF pada fresh profile dan toggle sama di kedua UI |
| Pilih Install extension ZIP saat OFF | Tidak membuka import; pengguna diarahkan mengaktifkan developer mode |
| Aktifkan developer mode | Nilai tetap tersimpan setelah restart; WebUI menampilkan nilai yang sama |
| Pilih ZIP lalu Cancel pada picker/konfirmasi | Tidak ada extension baru, import berikutnya tetap bisa berjalan |
| Install `hello-sharingan.zip` | Pesan sukses setelah registrasi; extension muncul di pengelola |
| Buka `https://example.com/` | Badge merah “Sharingan extension aktif” muncul |
| Buka popup extension | Timestamp dari service worker tampil; storage API bekerja |
| Restart browser; bersihkan hanya cache Android | Extension masih dimuat dan content script tetap bekerja setelah reload halaman |
| Disable melalui Extensions lalu reload halaman | Badge tidak muncul; enable lagi dan reload mengembalikannya |
| Remove melalui Extensions lalu reload halaman | Extension tidak terdaftar dan badge tidak muncul lagi |
| Toggle developer mode OFF setelah install | Import baru diblokir; extension lama tetap dikelola lewat enable/disable/remove |
| Install melalui Chrome Web Store | Periksa download, dialog permissions, enable/disable/remove; catat ID/version extension |

## Kasus negatif

- `missing-manifest.zip`, `nested-manifest.zip`, `invalid-manifest.zip`, `not-a-zip.zip`: gagal dengan pesan; tidak muncul toast sukses atau registrasi baru.
- `missing-script.zip`: unzip bisa berhasil tetapi validasi extension gagal. Pastikan tidak ada toast sukses prematur.
- `traversal.zip`: arsip tidak boleh menulis `sharingan-test-escape.txt` di luar direktori ekstraksi. Installer boleh menolak arsip atau melewati entry yang dilarang; yang diuji adalah tidak adanya penulisan keluar direktori. Gunakan perangkat/emulator debug untuk memeriksa filesystem privat secara sah.
- ZIP >64 MiB: copy dihentikan dan staging parsial dibuang.
- Izin URI ditolak/provider tidak tersedia: error tanpa crash.
- Tekan import berulang dan gunakan multiwindow: hanya satu staging/install Sharingan yang aktif.
- Matikan developer mode saat copy berjalan: native tidak memulai load baru.
- Putar layar saat picker/copy; tutup Activity saat install: tidak ada kebocoran Activity kuat; cek callback/error dan import berikutnya.
- Incognito: import melalui menu ditolak dan izin incognito extension tidak otomatis aktif.
- Extension dengan permission tidak didukung: harus dilaporkan/ditangani oleh subsystem extension, bukan dianggap otomatis kompatibel.
- ZIP bomb dan storage exhaustion: belum ada kuota hasil ekstraksi khusus; ini pekerjaan sebelum pelepasan ke pengguna umum.

## Unit test native yang relevan

Tree upstream memuat `ZipFileInstallerTest.ManifestExtractionFilter`, termasuk penolakan `test/manifest.json`, serta pengujian ZIP valid/invalid dan filter tipe file. Jalankan target test yang menyertakannya pada baseline yang berhasil dikompilasi. Test tersebut belum dijalankan di sesi ini; delapan test Python yang lulus hanya menguji tooling persiapan checkout.
