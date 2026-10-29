"""Penjelasan operasional rule QA/QC yang ditampilkan di MAGHES publik."""


CONDUCTOR_MISMATCH_GUIDANCE = {
    'Tiang vs JTM Conductor Mismatch': {
        'meaning': (
            'Titik tiang berpotongan tepat dengan satu atau lebih geometri JTM, tetapi nilai '
            '`kode_hantaran` pada tiang tidak sama dengan `description` pada seluruh kandidat '
            'JTM yang berpotongan dari layer pendukung terpilih.'
        ),
        'checks': ('kode_hantaran tiang', 'description JTM', 'posisi titik tiang terhadap garis JTM',
                   'layer/periode JTM yang dijadikan acuan'),
    },
    'Tiang vs JTR Conductor Mismatch': {
        'meaning': (
            'Titik tiang berpotongan tepat dengan satu atau lebih geometri JTR, tetapi nilai '
            '`kode_hantaran` pada tiang tidak sama dengan `description` pada seluruh kandidat '
            'JTR yang berpotongan dari layer pendukung terpilih.'
        ),
        'checks': ('kode_hantaran tiang', 'description JTR', 'posisi titik tiang terhadap garis JTR',
                   'layer/periode JTR yang dijadikan acuan'),
    },
}


def rule_guidance(label):
    return CONDUCTOR_MISMATCH_GUIDANCE.get(str(label))


def guidance_markdown(label):
    guidance = rule_guidance(label)
    if not guidance:
        return None
    checks = ', '.join(f'**{item}**' for item in guidance['checks'])
    return (
        f"**Arti temuan:** {guidance['meaning']}\n\n"
        "**Mengapa bisa muncul:** nilai atribut berbeda/typo atau formatnya tidak sama; "
        "titik tiang menempel pada ruas yang bukan pasangannya; geometri titik/garis kurang tepat; "
        "atau layer historis/pendukung yang dipilih belum merepresentasikan pasangan yang benar.\n\n"
        f"**Yang diperiksa admin:** {checks}.\n\n"
        "**Catatan:** MAGHES memakai perpotongan geometri persis (`ST_Intersects`) dan "
        "perbandingan teks apa adanya—tanpa toleransi jarak, `TRIM`, atau penyamaan huruf. "
        "Satu kandidat yang cocok dari layer terpilih sudah membuat tiang tidak dinyatakan mismatch. "
        "Temuan ini adalah indikasi konsistensi GIS, bukan bukti gangguan atau konektivitas listrik aktual."
    )

