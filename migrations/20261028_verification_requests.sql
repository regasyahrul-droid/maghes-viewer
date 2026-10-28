-- Jalankan sekali pada database publik dengan akun migrasi.
-- Akun aplikasi hanya memerlukan SELECT/INSERT pada tabel ini.
CREATE TABLE IF NOT EXISTS public.maghes_verification_requests (
    id uuid PRIMARY KEY,
    schema_name text NOT NULL CHECK (schema_name ~ '^[a-z]+_[0-9]{4}$'),
    table_name text NOT NULL CHECK (table_name ~ '^[A-Za-z0-9_]+$'),
    requested_by text NOT NULL,
    requester_email text NOT NULL,
    expected_rows bigint,
    notes text NOT NULL DEFAULT '',
    status text NOT NULL DEFAULT 'DIAJUKAN'
        CHECK (status IN ('DIAJUKAN','SEDANG_DIVERIFIKASI','HASIL_TERSEDIA','PERLU_PERBAIKAN','GAGAL_PUBLIKASI')),
    requested_at timestamptz NOT NULL DEFAULT now(),
    updated_at timestamptz NOT NULL DEFAULT now(),
    reviewer text,
    published_id bigint,
    published_score numeric(5,1),
    request_notified_at timestamptz,
    result_notified_at timestamptz
);
CREATE UNIQUE INDEX IF NOT EXISTS maghes_one_open_request_per_table
    ON public.maghes_verification_requests(schema_name, table_name)
    WHERE status IN ('DIAJUKAN','SEDANG_DIVERIFIKASI','GAGAL_PUBLIKASI');
CREATE INDEX IF NOT EXISTS maghes_requests_recent
    ON public.maghes_verification_requests(requested_at DESC);
-- Berikan SELECT/INSERT ke role koneksi MAGHES publik, SELECT/UPDATE ke role sinkronisasi UID.
-- Jangan memberikan UPDATE status kepada role koneksi MAGHES publik.

-- Rapor baru disembunyikan sampai seluruh batch error berhasil diunggah.
ALTER TABLE public.tbl_published_verifications
    ADD COLUMN IF NOT EXISTS is_complete boolean NOT NULL DEFAULT true;
ALTER TABLE public.tbl_published_verifications
    ADD COLUMN IF NOT EXISTS request_id uuid REFERENCES public.maghes_verification_requests(id);
CREATE INDEX IF NOT EXISTS maghes_published_request_id
    ON public.tbl_published_verifications(request_id);
