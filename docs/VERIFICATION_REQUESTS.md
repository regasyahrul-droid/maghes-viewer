# Pengajuan verifikasi MAGHES publik

Perubahan ini disiapkan untuk alur admin UP3 → verifikator UID → hasil publik. Branch ini **belum boleh digabung ke main** sebelum prasyarat berikut dipenuhi, karena login baru membaca akun dari Streamlit secrets dan halaman hasil baru membaca kolom `is_complete`.

## Prasyarat penerapan

1. Jalankan `migrations/20261028_verification_requests.sql` pada database publik dengan akun migrasi. Periksa skema tabel hasil yang sudah ada dan hak role sebelum menjalankan.
2. Di Streamlit Cloud, isi Secrets tanpa menaruh rahasia di GitHub:
   - `SUPABASE_DB_URL`: URL koneksi database publik yang saat ini aktif. Pertahankan nilai yang benar dari konfigurasi aplikasi sekarang.
   - `GMAIL_SENDER`: alamat Gmail pengirim yang disepakati.
   - `GMAIL_APP_PASSWORD`: sandi aplikasi Gmail khusus MAGHES; jangan gunakan sandi login Gmail biasa.
   - `REVIEWER_EMAIL`: alamat email verifikator UID.
   - `accounts.<username>.password_hash`, `role`, `schema`, dan `email` untuk setiap akun admin UP3. Email akun harus terverifikasi oleh pengelola sebelum notifikasi hasil dipakai.
3. Beri role database aplikasi publik izin SELECT/INSERT pada `maghes_verification_requests`, dan UPDATE terbatas pada `request_notified_at`. Akun sinkronisasi UID perlu SELECT/UPDATE status dan metadata hasil. Aplikasi publik tidak boleh mengubah status verifikasi.
4. Pada MAGHES intranet, sediakan `MAGHES_GMAIL_SENDER` dan `MAGHES_GMAIL_APP_PASSWORD` lewat environment proses atau konfigurasi privat terenkripsi. Server UID harus bisa mengakses SMTP Gmail di port 587.
5. Pastikan hash akun publik cocok dengan password yang akan tetap dipakai. Kredensial lama pernah berada di histori repo yang public; rencanakan rotasi akun publik dan koneksi database. Jangan menyalin password lama ke commit baru.

Pengelola PC mempunyai template rahasia lokal di `C:/Users/regag/.maghes/public-viewer-secrets-template.toml`. File itu berisi hash dari konfigurasi privat MAGHES lokal dan placeholder untuk email UP3. Jangan commit atau kirim file tersebut ke GitHub. Nilai database dan sandi aplikasi Gmail masih perlu diisi melalui Streamlit Cloud Secrets.

## Alur

Admin mengunggah tabel lewat QGIS, lalu mengajukan nama tabel yang tepat di portal publik. Satu target hanya mempunyai satu pengajuan aktif. Pengajuan tersimpan walau pengiriman email UID gagal; admin dapat mencoba kirim ulang. Verifikator UID melihat antrean di halaman intranet, memeriksa keberadaan tabel dan jumlah record, lalu membuka Validator.

Rapor publik baru diberi `is_complete=false` lebih dahulu. Setelah seluruh batch error terkirim, penanda menjadi `true`. Portal publik hanya menampilkan rapor lengkap. Setelah penanda lengkap dan status pengajuan diperbarui, MAGHES UID mengirim email hasil kepada admin. Bila email gagal, hasil tetap tersedia dan pengiriman dapat dicoba ulang dari antrean UID.

Email berisi ringkasan dan tautan ke portal. Rincian aset dan data pelanggan tetap dibaca sesudah login.

## Pengujian penerapan

- Coba satu akun UP3 yang terdaftar; pastikan ia hanya melihat schema sendiri.
- Ajukan tabel uji yang telah selesai diunggah; cek satu baris pengajuan dan satu email UID.
- Jalankan verifikasi UID; cek bahwa rapor tersembunyi ketika batch error gagal, lalu tampil setelah lengkap.
- Cek email admin, tautan hasil, dan pengiriman ulang tanpa verifikasi ulang.
- Uji penolakan login, pengajuan duplikat, dan email belum terkonfigurasi.

Kode branch dapat ditinjau tanpa menjalankan migrasi atau mengirim email sungguhan.
