from django.test import TestCase
from django.core.files.base import ContentFile
from django.contrib.auth.models import User

import filebox.models
from filebox.models import FileMetaData, FileContent

class TestFileContent(TestCase):
    def setUp(self):
        self.user = User.objects.create(username='ilya')

    def tearDown(self):
        self.user.delete()

    def test_refcnt(self):
        content = ContentFile('Hello, World!', name='test.txt')

        args = { 'contentfile': content, 'user': self.user }
        FileMetaData.objects.create_with_content(filename='file1', **args)
        FileMetaData.objects.create_with_content(filename='file2', **args)

        self.assertEqual(FileContent.objects.count(), 1)

        FileMetaData.objects.filter(filename='file2').delete()
        self.assertEqual(FileContent.objects.count(), 1)

        FileMetaData.objects.filter(filename='file1').delete()
        self.assertEqual(FileContent.objects.count(), 0)

    def test_hash_collision(self):
        # Testing that we won't deduplicate files in case of SHA-1 collision

        # monkey patching sha1 calculation code
        original = filebox.models._sha1_of_file
        filebox.models._sha1_of_file = lambda file: 'fake-sha1'

        try:
            content1 = ContentFile('Content one', name='test1.txt')
            content2 = ContentFile('Content two', name='test1.txt')

            FileMetaData.objects.create_with_content(contentfile=content1, user=self.user, filename='test1.txt')
            FileMetaData.objects.create_with_content(contentfile=content2, user=self.user, filename='test1.txt')

            self.assertEqual(FileContent.objects.count(), 2)

            FileMetaData.objects.all().delete()
        finally:
            filebox.models._sha1_of_file = original
