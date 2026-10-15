import re
import tempfile
import unittest
import xml.etree.ElementTree as ET
from unittest.mock import patch

from bs4 import BeautifulSoup

from main import Utils


XHTML = '{http://www.w3.org/1999/xhtml}'


class ContentPreservationTests(unittest.TestCase):
    def convert(self, source):
        with tempfile.TemporaryDirectory() as directory:
            with patch('main.requests.get', side_effect=AssertionError('Unexpected network request')):
                return Utils().disable_internal_hrefs(source, directory, 'Example')

    def test_ellipsis_does_not_remove_remaining_paragraph_or_inline_markup(self):
        source = '<h1>Example</h1><p>Wait... keep <strong>this text</strong> and the ending.</p>'
        result = BeautifulSoup(self.convert(source), 'xml')
        self.assertEqual('Wait... keep this text and the ending.', ' '.join(result.p.stripped_strings))
        self.assertEqual('this text', result.strong.get_text(strip=True))

    def test_preformatted_code_keeps_nested_content_order_and_whitespace(self):
        source = ('<html xmlns="http://www.w3.org/1999/xhtml"><body>'
                  '<p>Before</p><pre>first...\n<code>call(<span>argument</span>)</code>\nlast...</pre>'
                  'tail<p>After</p></body></html>')
        original = ET.fromstring(source)
        result = ET.fromstring(Utils.filter_attributes(source))
        pre = result.find('.//' + XHTML + 'pre')
        self.assertIsNotNone(pre)
        self.assertEqual('first...\ncall(argument)\nlast...', ''.join(pre.itertext()))
        self.assertEqual(''.join(original.itertext()), ''.join(result.itertext()))
        self.assertIsNotNone(pre.find(XHTML + 'code/' + XHTML + 'span'))

    def test_links_image_descriptions_and_table_list_attributes_survive(self):
        source = ('<h1>Example</h1><p><a href="https://example.org/reference">Reference</a></p>'
                  '<img alt="Diagram description"/>'
                  '<table><colgroup><col span="2"/></colgroup>'
                  '<tr><td colspan="2" rowspan="3">Merged cell</td></tr></table>'
                  '<ol start="4"><li value="6">Numbered item</li></ol>')
        result = BeautifulSoup(self.convert(source), 'xml')
        self.assertEqual('https://example.org/reference', result.a['href'])
        self.assertEqual('Diagram description', result.img['alt'])
        self.assertEqual('2', result.td['colspan'])
        self.assertEqual('3', result.td['rowspan'])
        self.assertEqual('2', result.col['span'])
        self.assertEqual('4', result.ol['start'])
        self.assertEqual('6', result.li['value'])

    def test_full_cleanup_preserves_code_elements_and_surrounding_text(self):
        source = ('<h1>Example</h1><p>Before...</p>'
                  '<pre><code>print(<span>"value..."</span>)</code></pre><p>After...</p>')
        result = BeautifulSoup(self.convert(source), 'xml')
        self.assertIsNotNone(result.pre)
        self.assertIsNotNone(result.pre.code.span)
        normalize = lambda value: re.sub(r'\s+', ' ', value).strip()
        expected = normalize(BeautifulSoup(source, 'html.parser').get_text(' ', strip=True))
        self.assertEqual(expected, normalize(result.body.get_text(' ', strip=True)))


if __name__ == '__main__':
    unittest.main()
