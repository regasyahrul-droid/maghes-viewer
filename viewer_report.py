"""Laporan QA/QC publik dari snapshot intranet, tanpa menjalankan verifikasi."""
import json
import numbers

import pandas as pd
import streamlit as st


def unpack(value, default=None):
    if isinstance(value, (dict, list)):
        return value
    if isinstance(value, str) and value:
        try:
            return json.loads(value)
        except ValueError:
            pass
    return {} if default is None else default


def duplicate_group(label):
    value = label.upper()
    if 'DUPLIKAT' not in value and 'DUPLICATE' not in value:
        return None
    return 'geometry' if any(word in value for word in ('GEOMETRY', 'GEOMETRI', 'LINE')) else 'identity'


def numeric(value):
    return isinstance(value, numbers.Real) and not isinstance(value, bool) and pd.notna(value)


def detail_table(rows, key, filename):
    frame = rows.copy() if isinstance(rows, pd.DataFrame) else pd.DataFrame(rows)
    if frame.empty:
        st.info('Rincian record tidak tersimpan pada laporan ini.')
        return
    visible = frame.drop(columns=['geom_wkt'], errors='ignore')
    st.dataframe(visible, use_container_width=True, hide_index=True)
    st.download_button('Download CSV (Excel)', visible.to_csv(index=False).encode('utf-8-sig'),
                       filename, 'text/csv', key=key)


def render_rules(summary, details, prefix, table, errors):
    if not summary:
        st.warning('Ringkasan pemeriksaan belum tersedia pada laporan ini.')
        return
    st.dataframe(pd.DataFrame([{'Aturan': label, 'Temuan / Status': str(value)}
                               for label, value in summary.items() if not duplicate_group(label)]),
                 use_container_width=True, hide_index=True)
    for index, (label, value) in enumerate(summary.items()):
        if duplicate_group(label):
            continue
        if numeric(value) and value == 0:
            continue
        if numeric(value):
            st.error(f'{label}: {value:,.0f} error')
        else:
            st.warning(f'{label}: {value}')
        rows = details.get(label, [])
        if not rows and not errors.empty and 'rule_dilanggar' in errors:
            rows = errors[errors['rule_dilanggar'].eq(label)].to_dict('records')
        if rows:
            with st.expander(f'Lihat detail / Download — {label}'):
                if numeric(value) and len(rows) < value:
                    st.caption(f'Rincian tersimpan {len(rows)} dari {value:,.0f} temuan. Log error terpadu tersedia pada tab terakhir.')
                detail_table(rows, f'{prefix}_{index}_{table}', f'{prefix}_{label}_{table}.csv')


def duplicate_rules(snapshot, group):
    spatial, attr = snapshot.get('spatial', {}), snapshot.get('attribute', {})
    result = {label: (count, spatial.get('topo_details', {}).get(label, []))
              for label, count in spatial.get('topo_summary', {}).items() if duplicate_group(label) == group}
    if not result:
        result = {label: (count, attr.get('details', {}).get(label, []))
                  for label, count in attr.get('summary', {}).items() if duplicate_group(label) == group}
    return result


def render_duplicates(snapshot, table, layer_type):
    for group, title in [('geometry', 'Duplikasi Geometri'),
                         ('identity', 'Duplikasi ID Pelanggan' if layer_type in ('pelanggan_app', 'app', 'pelanggan') else 'Duplikasi Identitas Aset')]:
        rules = duplicate_rules(snapshot, group)
        if not rules:
            st.info(f'{title}: hasil pemeriksaan belum tersedia.')
            continue
        total = sum(value for value, _ in rules.values() if numeric(value))
        if total == 0 and all(numeric(value) for value, _ in rules.values()):
            st.success(f'{title}: 0 temuan')
            continue
        st.error(f'{title}: {total:,.0f} temuan')
        with st.expander(f'Lihat detail / Download — {title}'):
            st.caption('Temuan aturan dapat tumpang tindih. Rincian maksimal 500 record per aturan, sama seperti rapor intranet. Pasangan duplikat diperiksa pada data saat snapshot dikirim; maksimal 10 ID pasangan per sumber.')
            note = snapshot.get('duplicate_notes', {}).get(group)
            if note:
                st.warning(note)
            rows = snapshot.get('duplicates', {}).get(group, [])
            if not rows:
                rows = [dict(row, aturan_duplikasi=label) for label, (_, records) in rules.items() for row in records]
            frame = pd.DataFrame(rows)
            if 'layer_duplikasi' in frame:
                options = sorted(frame['layer_duplikasi'].dropna().astype(str).unique())
                selected = st.multiselect('Filter layer duplikasi', options, default=options, key=f'dup_filter_{group}_{table}')
                frame = frame[frame['layer_duplikasi'].isin(selected)]
            detail_table(frame, f'dup_{group}_{table}', f'duplikasi_{group}_{table}.csv')


def render_report(record, render_card, legacy_errors=None):
    table = record['tabel_sumber']
    key = str(record['id'])
    recap = unpack(record.get('hasil_rekapitulasi'))
    snapshot = recap.get('_qa_report', {})
    errors = pd.DataFrame(snapshot.get('error_log', [])) if snapshot else (
        legacy_errors.copy() if legacy_errors is not None else pd.DataFrame())
    if 'detail_error' in errors and 'detail_anomali' not in errors:
        errors = errors.rename(columns={'detail_error': 'detail_anomali'})
    if snapshot:
        st.caption(f"Verifikator: {snapshot.get('run_by', '—')} · Waktu verifikasi: {snapshot.get('run_at', '—')}")
    else:
        st.warning('Laporan lama belum memuat seluruh rincian intranet. Rincian yang sudah dipublikasikan tetap ditampilkan.')
    notes = recap.get('_qa_checks', [])
    if notes:
        st.warning('Verifikasi selesai dengan catatan. Sebagian pemeriksaan belum tersedia dan skor terkait belum dapat dihitung.')
        st.dataframe(pd.DataFrame(notes), use_container_width=True, hide_index=True)
    tabs = st.tabs(['📈 Rekapitulasi Aset', '📐 Struktur Kolom', '📊 Kualitas Atribut',
                    '🌐 Spasial & Duplikat', '📋 Error Log Terpadu'])
    with tabs[0]:
        st.markdown('### Rekapitulasi Aset')
        st.metric('Total Record Diverifikasi', int(record.get('total_record') or 0))
        groups = [(name, rows) for name, rows in recap.items() if not name.startswith('_')]
        for index, (name, rows) in enumerate(groups):
            frame = pd.DataFrame(rows)
            st.markdown(f'#### {name}')
            if not frame.empty:
                numbers_ = frame.select_dtypes(include='number').columns.tolist()
                if len(frame) > 1 and len(frame.columns) > 1 and numbers_:
                    chart = frame.copy()
                    chart.iloc[:, 0] = chart.iloc[:, 0].fillna('Tidak diisi').astype(str)
                    st.bar_chart(chart.set_index(chart.columns[0])[numbers_[-1]])
                detail_table(frame, f'recap_{index}_{key}', f'rekap_{index}_{table}.csv')
        if not groups:
            st.info('Rincian pengelompokan aset belum tersedia; jumlah record tetap ditampilkan di atas.')
    with tabs[1]:
        st.markdown('### Perbandingan Struktur Kolom')
        structure = pd.DataFrame(snapshot.get('structure') or unpack(record.get('hasil_struktur'), []))
        if structure.empty or 'status' not in structure:
            st.warning('Hasil perbandingan struktur belum tersedia.')
        else:
            issues = structure[structure['status'].ne('OK')]
            score = (len(structure) - len(issues)) / len(structure) * 100
            st.markdown(render_card('Validitas Struktur Kolom', score), unsafe_allow_html=True)
            st.caption(f'{len(structure)} kolom · {len(structure)-len(issues)} sesuai · {len(issues)} bermasalah')
            if issues.empty:
                st.success('Seluruh kolom pembanding sesuai.')
            else:
                st.error(f'{len(issues)} kolom bermasalah')
                detail_table(issues, f'structure_issues_{key}', f'struktur_bermasalah_{table}.csv')
            with st.expander('Lihat seluruh kolom'):
                detail_table(structure, f'structure_all_{key}', f'struktur_{table}.csv')
    with tabs[2]:
        st.markdown('### Kualitas Atribut')
        st.markdown(render_card('Validitas Atribut', record.get('score_attr')), unsafe_allow_html=True)
        attr = snapshot.get('attribute', {})
        attribute_errors = errors[errors['jenis_error'].eq('ATRIBUT')] if 'jenis_error' in errors else pd.DataFrame()
        summary = attr.get('summary') or (attribute_errors['rule_dilanggar'].value_counts().to_dict() if not attribute_errors.empty else {})
        render_rules(summary, attr.get('details', {}), f'attr_{key}', table, attribute_errors)
    with tabs[3]:
        st.markdown('### Analitik Spasial & Topologi')
        st.markdown(render_card('Validitas Spasial', record.get('score_spas')), unsafe_allow_html=True)
        spatial = snapshot.get('spatial', {})
        if spatial.get('tipe_geom'):
            st.markdown('#### Tipe Geometri')
            st.dataframe(pd.DataFrame(spatial['tipe_geom']), use_container_width=True, hide_index=True)
        render_duplicates(snapshot, key, record.get('layer_type'))
        st.markdown('#### Topologi Jaringan & Kedekatan')
        spatial_errors = errors[errors['jenis_error'].ne('ATRIBUT')] if 'jenis_error' in errors else pd.DataFrame()
        summary = spatial.get('topo_summary') or (spatial_errors['rule_dilanggar'].value_counts().to_dict() if not spatial_errors.empty else {})
        render_rules(summary, spatial.get('topo_details', {}), f'spatial_{key}', table, spatial_errors)
    with tabs[4]:
        st.markdown(render_card('Kesehatan Data Keseluruhan', record.get('score_overall')), unsafe_allow_html=True)
        st.markdown('### Error Log Terpadu & Tindak Lanjut')
        if errors.empty:
            st.info('Tidak ada record error tersimpan pada snapshot ini. Periksa juga catatan pemeriksaan yang belum tersedia.')
        else:
            status = st.selectbox('Filter Status Revisi', ['OPEN', 'Semua', 'CLOSED'], key=f'status_{key}')
            shown = errors if status == 'Semua' or 'status_revisi' not in errors else errors[errors['status_revisi'].eq(status)]
            kinds = sorted(shown['jenis_error'].dropna().unique()) if 'jenis_error' in shown else []
            selected = st.multiselect('Jenis error', kinds, default=kinds, key=f'kinds_{key}')
            if 'jenis_error' in shown:
                shown = shown[shown['jenis_error'].isin(selected)]
            st.caption(f'{len(shown)} log sesuai filter dari {len(errors)} log tersimpan.')
            detail_table(shown, f'errors_{key}', f'error_log_{table}.csv')
            geo = snapshot.get('error_geojson', {})
            if geo.get('features'):
                # Apply the same record/rule filter to the geometry export.
                allowed = {(str(r.get('objectid')), r.get('rule_dilanggar'), r.get('jenis_error'), r.get('status_revisi'))
                           for r in shown.to_dict('records')}
                features = [f for f in geo['features'] if (str(f['properties'].get('objectid')), f['properties'].get('rule'),
                            f['properties'].get('jenis_error'), f['properties'].get('status_revisi')) in allowed]
                filtered_geo = {'type': 'FeatureCollection', 'features': features}
                st.download_button('Download GeoJSON (QGIS)', json.dumps(filtered_geo),
                                   f'error_log_{table}.geojson', 'application/geo+json', key=f'geo_{key}')
                if features:
                    with st.expander('Peta sebaran error'):
                        import pydeck as pdk
                        st.caption('Peta menampilkan maksimal 1.000 geometri. Download memuat seluruh geometri sesuai filter.')
                        st.pydeck_chart(pdk.Deck(layers=[pdk.Layer('GeoJsonLayer',
                            {'type': 'FeatureCollection', 'features': features[:1000]}, pickable=True,
                            get_fill_color=[230, 60, 60, 160], get_line_color=[230, 60, 60],
                            point_radius_min_pixels=5, line_width_min_pixels=2)],
                            initial_view_state=pdk.ViewState(latitude=-7.15, longitude=110.14, zoom=8),
                            tooltip={'text': 'ID: {properties.objectid}\nRule: {properties.rule}\nDetail: {properties.detail}'},
                            map_style='light'))
            if snapshot.get('geometry_note'):
                st.warning(snapshot['geometry_note'])
    refs = snapshot.get('spatial', {}).get('reference_config')
    if refs:
        with st.expander('Acuan dan layer pendukung yang digunakan'):
            for source in refs.get('sources', []):
                st.write(f"{source['schema']}.{source['table']}")
            for kind, sources in refs.get('support_sources', {}).items():
                st.write(f'Pendukung {kind}')
                for source in sources:
                    st.write(f"{source['schema']}.{source['table']}")

