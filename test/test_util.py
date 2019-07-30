import unittest

from unittest.mock import Mock

import util

class TestUtil(unittest.TestCase):

    def setUp(self):
        pass

    def test_remove_punctuation(self):
        self.assertEqual(
            util.remove_punctuation('a!b@c#d$e%f^g&h*i'),
            'abcdefghi'
        )

    def test_split_command(self):
        msg = Mock()

        msg.content = '!test'
        self.assertEqual(util.split_command(msg), ('test', None))

        msg.content = '!test foo'
        self.assertEqual(util.split_command(msg), ('test', 'foo'))

        msg.content = '!test foo bar'
        self.assertEqual(util.split_command(msg), ('test', 'foo bar'))

    def test_truncate(self):
        self.assertEqual(
            util.truncate('abcdefghijklmnopqrstuvwxyz', 5),
            'abcd…'
        )

    def test_is_get(self):
        self.assertTrue(util.is_get(123))
        self.assertTrue(util.is_get(12345))
        self.assertTrue(util.is_get(123456789))
        self.assertTrue(util.is_get(1233))
        self.assertTrue(util.is_get(22))
        self.assertTrue(util.is_get(333))
        self.assertTrue(util.is_get(55555))

    def test_ts_to_iso(self):
        self.assertEqual(util.ts_to_iso(0), '1969-12-31T19:00:00')
        self.assertEqual(
            util.ts_to_iso(1539017270.88595),
            '2018-10-08T12:47:50.885950'
        )

    def test_td_str(self):
        self.assertEqual(util.td_str(12345), '3:25:45')

    def test_is_embeddable_image_url(self):
        # pylint: disable=unnecessary-lambda
        t = lambda s: util.is_embeddable_image_url(s)
        self.assertTrue(t('https://example.com/image.png'))
        self.assertFalse(t('https://example.com/'))
        self.assertFalse(t('https://example.com/file.txt'))
        self.assertFalse(t('ftp://example.com/image.png'))
        self.assertFalse(t('invalid'))

if __name__ == "__main__":
    unittest.main()
