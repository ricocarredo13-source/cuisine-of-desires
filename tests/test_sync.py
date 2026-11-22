import importlib.util
from pathlib import Path
import unittest

spec = importlib.util.spec_from_file_location('sync_notion', str(Path(__file__).parents[1] / 'scripts' / 'sync_notion.py'))
mod = importlib.util.module_from_spec(spec)
spec.loader.exec_module(mod)

def text(value):
    return [{'plain_text': value, 'text': {'content': value}, 'annotations': {}}]

def block(t, value, **kwargs):
    return {'id': 'f00baaaa-bbbb-cccc-dddd-eeeeeeeeeeee', 'type': t, t: {'rich_text': text(value), **kwargs}}

class SyncTests(unittest.TestCase):
    def test_compile_content(self):
        page = {'properties': {'title': {'type':'title','title':text('Cuisine of Desires')}}}
        blocks = [block('heading_1','Chocolate Chip Cookie to Satisfy Your Hunger'),
                  block('paragraph','By Group 4 · November 23, 2026'),
                  block('heading_2','Introduction'),block('paragraph','Some appetites are easier to satisfy than others.'),
                  block('heading_2','Ingredients'),block('paragraph','2 cups flour')]
        result = mod.compile_content(page,blocks,[block('paragraph','About our class')])
        self.assertEqual(result['brand'], 'Cuisine of Desires')
        self.assertEqual(len(result['sections']), 2)
        self.assertEqual(result['sections'][1]['id'], 'ingredients')
        self.assertIn('2 cups flour', result['sections'][1]['html'])
        self.assertIn('About our class',result['aboutHtml'])
    def test_escapes_untrusted_notion_text(self):
        self.assertIn('&lt;script&gt;',mod.rich_html(text('<script>')))
        self.assertEqual(mod.clean_url('javascript:alert(1)'), '')
        self.assertEqual(mod.clean_url('https://example.com'), 'https://example.com')
    def test_youtube_embed(self):
        self.assertIn('youtube-nocookie.com/embed/abcdEFG1234',mod.video_html('https://www.youtube.com/watch?v=abcdEFG1234'))
    def test_list_numbering(self):
        s = mod.render_blocks([block('numbered_list_item','Mix'), block('numbered_list_item','Bake')])
        self.assertEqual(s.count('<ol>'),1)
        self.assertEqual(s.count('<li>'),2)

if __name__ == '__main__':
    unittest.main()
