import json
import unittest

from streamlit.testing.v1 import AppTest
from viewer_report import unpack, duplicate_rules
from rule_guidance import guidance_markdown


def fixture():
    snapshot = {
        'run_by': 'verifier', 'run_at': '2026-10-29',
        'structure': [{'kolom': 'id', 'status': 'OK'}, {'kolom': 'vertex', 'status': 'KOLOM HILANG'}],
        'attribute': {'summary': {'DATE': 1, 'REQUIRED': 'KOLOM HILANG', 'VALID': 0},
                      'details': {'DATE': [{'id': 7, 'description': 'Example', 'date': None}]}},
        'spatial': {'tipe_geom': [{'geom_type': 'POINT', 'total': 2}],
                    'topo_summary': {'Duplikat Geometry (Internal)': 2, 'Gardu Tanpa Tiang': 1},
                    'topo_details': {'Gardu Tanpa Tiang': [{'id': 7, 'description': 'Example'}]}},
        'duplicates': {'geometry': [
            {'id': 7, 'layer_duplikasi': 'master_jateng.TIANG', 'id_pasangan': '10'},
            {'id': 8, 'layer_duplikasi': 'unit.ADD_TIANG', 'id_pasangan': '20'}]},
        'error_log': [{'objectid': 7, 'description_aset': 'Example', 'jenis_error': 'ATRIBUT',
                       'rule_dilanggar': 'DATE', 'detail_anomali': 'Missing date', 'status_revisi': 'OPEN'},
                      {'objectid': 8, 'description_aset': 'Example 2', 'jenis_error': 'SPASIAL',
                       'rule_dilanggar': 'Gardu Tanpa Tiang', 'detail_anomali': 'No pole', 'status_revisi': 'CLOSED'}],
        'error_geojson': {'type': 'FeatureCollection', 'features': [{
            'type': 'Feature', 'geometry': {'type': 'Point', 'coordinates': [110, -7]},
            'properties': {'objectid': 7, 'rule': 'DATE', 'detail': 'Missing date',
                           'jenis_error': 'ATRIBUT', 'status_revisi': 'OPEN'}}]},
    }
    record = {'id': 99, 'tabel_sumber': '202610_ADD_GARDU', 'total_record': 2,
              'layer_type': 'gardu_distribusi', 'score_attr': None, 'score_spas': 75,
              'score_overall': None, 'hasil_struktur': None,
              'hasil_rekapitulasi': json.dumps({'Total Aset': [{'Jenis Aset': 'GARDU', 'Jumlah Record': 2}],
                                               '_qa_report': snapshot})}
    return record


class PublicReportViewTests(unittest.TestCase):
    def test_all_tabs_render_partial_report_and_duplicate_filter(self):
        app = AppTest.from_string('''
import streamlit as st
from viewer_report import render_report
render_report(st.session_state['record'], lambda title, score: f'<p>{title}: {score}</p>')
''')
        app.session_state['record'] = fixture()
        app.run(timeout=20)
        self.assertEqual(len(app.exception), 0)
        self.assertEqual(len(app.tabs), 5)
        app.multiselect(key='dup_filter_geometry_99').set_value(['master_jateng.TIANG']).run()
        self.assertEqual(len(app.exception), 0)
        frames = [item.value for item in app.dataframe if 'layer_duplikasi' in item.value]
        self.assertEqual(len(frames), 1)
        self.assertEqual(frames[0]['layer_duplikasi'].tolist(), ['master_jateng.TIANG'])
        self.assertTrue(any('description_aset' in item.value for item in app.dataframe))

    def test_topology_duplicate_summary_has_priority_over_attribute_fallback(self):
        snapshot = unpack(fixture()['hasil_rekapitulasi'])['_qa_report']
        snapshot['attribute']['summary']['DUPLICATE_GEOMETRY'] = 999
        rules = duplicate_rules(snapshot, 'geometry')
        self.assertEqual(len(rules), 1)
        self.assertEqual(next(iter(rules.values()))[0], 2)

    def test_public_conductor_guidance_matches_qa_rule(self):
        text = guidance_markdown('Tiang vs JTM Conductor Mismatch')
        self.assertIn('kode_hantaran', text)
        self.assertIn('description JTM', text)
        self.assertIn('ST_Intersects', text)
        self.assertIsNone(guidance_markdown('Gardu Tanpa Tiang'))

    def test_conductor_guidance_panel_is_rendered_with_finding(self):
        app = AppTest.from_string('''
import pandas as pd
from viewer_report import render_rules
render_rules({'Tiang vs JTM Conductor Mismatch': 86}, {}, 'spatial', 'TIANG', pd.DataFrame())
''').run(timeout=20)
        self.assertEqual(len(app.exception), 0)
        self.assertTrue(any('Apa arti Tiang vs JTM' in item.label for item in app.expander))


if __name__ == '__main__':
    unittest.main()

