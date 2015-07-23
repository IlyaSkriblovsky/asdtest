# -*- coding: utf-8 -*-

from django.test import TestCase, override_settings
from django.core.files.base import ContentFile
from django.contrib.auth.models import User
from django.contrib.messages.storage.base import Message
from django.contrib.messages.constants import INFO, SUCCESS
from django.conf import settings

import filebox.models
from filebox.models import FileMetaData, FileContent

class TestFileContent(TestCase):

    @classmethod
    def setUpTestData(cls):
        cls.user = User.objects.create(username='vasya')

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
            contents = [
                ContentFile('Content one', name='test1.txt'),
                ContentFile('Content two', name='test1.txt'),
                ContentFile('Content three', name='test1.txt'),
            ]

            for content in contents:
                FileMetaData.objects.create_with_content(contentfile=content, user=self.user, filename='test1.txt')

            self.assertEqual(FileContent.objects.count(), len(contents))

            FileMetaData.objects.all().delete()
        finally:
            filebox.models._sha1_of_file = original


class TestFileList(TestCase):

    @staticmethod
    def create_user_with_files(username, password):
        user = User.objects.create_user(username, password=password)
        for i in range(5):
            FileMetaData.objects.create_with_content(
                contentfile=ContentFile('Hello, World! ' + str(i), name='test.txt' + str(i)),
                filename='test.txt' + str(i),
                user=user
            )
        return user

    @classmethod
    def setUpTestData(cls):
        cls.vasya = cls.create_user_with_files('vasya', 'vasya')
        cls.petya = cls.create_user_with_files('petya', 'petya')

    def setUp(self):
        self.client.login(username='vasya', password='vasya')

    def test_get(self):
        response = self.client.get('/')
        self.assertEqual(response.status_code, 200)
        self.assertTemplateUsed(response, 'filebox/filemetadata_list.html')

        self.assertQuerysetEqual(
            response.context['object_list'],
            FileMetaData.objects.filter(user=self.vasya),
            transform=lambda x: x,
        )


class TestUploadForm(TestCase):

    @classmethod
    def setUpTestData(cls):
        cls.vasya = User.objects.create_user(username='vasya', password='vasya')
        cls.petya = User.objects.create_user(username='petya', password='petya')

    def setUp(self):
        self.testcontent = ContentFile('Hello, World!', name='test.txt')

        self.assertTrue(self.client.login(username='vasya', password='vasya'))

    def test_get(self):
        response = self.client.get('/upload')
        self.assertEqual(response.status_code, 200)
        self.assertTemplateUsed(response, 'filebox/filemetadata_form.html')

    def test_upload(self):
        response = self.client.post('/upload', { 'content': self.testcontent }, follow=True)
        self.assertEqual(response.status_code, 200)
        self.assertRedirects(response, '/')

        md = FileMetaData.objects.get(user=self.vasya)
        self.assertEqual(md.filename, self.testcontent.name)

        self.testcontent.seek(0)
        self.assertEqual(md.content.content.read(), self.testcontent.read())

    def test_empty(self):
        response = self.client.post('/upload')
        self.assertEqual(response.status_code, 200)
        self.assertTemplateUsed(response, 'filebox/filemetadata_form.html')
        self.assertFormError(response, 'form', 'content', u'Обязательное поле.')

    def test_maxfiles(self):
        filecontent = FileContent.objects.create(content=self.testcontent)
        FileMetaData.objects.bulk_create(
            [FileMetaData(user=self.vasya, filename='test.txt', content=filecontent)] * settings.FILEBOX_MAX_FILES_PER_USER
        )

        self.testcontent.seek(0)
        response = self.client.post('/upload', { 'content': self.testcontent })
        self.assertEqual(response.status_code, 200)
        self.assertTemplateUsed(response, 'filebox/filemetadata_form.html')
        self.assertFormError(response, 'form', None, u'Вы не можете загрузить более {0} файлов'.format(settings.FILEBOX_MAX_FILES_PER_USER))

    def test_duplicate_message(self):
        FileMetaData.objects.create_with_content(user=self.petya, filename='test.txt', contentfile=self.testcontent)

        self.testcontent.seek(0)
        response = self.client.post('/upload', { 'content': self.testcontent }, follow=True)
        self.assertEqual(response.status_code, 200)
        self.assertRedirects(response, '/')
        self.assertIn(Message(INFO, u'Этот файл уже есть у пользователя petya'), response.context['messages'])

        self.testcontent.seek(0)
        response = self.client.post('/upload', { 'content': self.testcontent }, follow=True)
        self.assertEqual(response.status_code, 200)
        self.assertRedirects(response, '/')
        self.assertIn(Message(INFO, u'Этот файл уже есть у пользователя petya'), response.context['messages'])
        self.assertIn(Message(INFO, u'Этот файл уже есть в вашем хранилище'), response.context['messages'])


class TestDeleteFile(TestCase):

    @classmethod
    def setUpTestData(cls):
        cls.vasya  = User.objects.create_user(username='vasya', password='vasya')
        cls.file1 = FileMetaData.objects.create_with_content(
            contentfile=ContentFile('Hello, World!', name='test.txt'),
            filename='test.txt',
            user=cls.vasya
        )

        cls.petya  = User.objects.create_user(username='petya', password='petya')
        cls.file2 = FileMetaData.objects.create_with_content(
            contentfile=ContentFile('Hello, World!', name='test.txt'),
            filename='test.txt',
            user=cls.petya
        )

    def setUp(self):
        self.client.login(username='vasya', password='vasya')

    def test_get(self):
        response = self.client.get('/delete/' + str(self.file1.id))
        self.assertEqual(response.status_code, 200)
        self.assertTemplateUsed(response, 'filebox/filemetadata_confirm_delete.html')

    def test_post(self):
        response = self.client.post('/delete/' + str(self.file1.id), follow=True)
        self.assertEqual(response.status_code, 200)
        self.assertRedirects(response, '/')
        self.assertIn(Message(SUCCESS, u'Файл "test.txt" удалён из вашего хранилища'), response.context['messages'])

        self.assertEqual(FileMetaData.objects.count(), 1)

    def test_delete_others(self):
        response = self.client.post('/delete/' + str(self.file2.id))
        self.assertEqual(response.status_code, 404)

        self.assertEqual(FileMetaData.objects.count(), 2)


class TestDownloadFile(TestCase):

    @classmethod
    def setUpTestData(cls):
        cls.vasya  = User.objects.create_user(username='vasya', password='vasya')
        cls.file1 = FileMetaData.objects.create_with_content(
            contentfile=ContentFile('Hello, World!', name='test.txt'),
            filename='test.txt',
            user=cls.vasya
        )

    def test_download(self):
        response = self.client.get('/download/{0}/test.txt'.format(self.file1.id))
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.content, self.file1.content.content.read())
        self.assertEqual(response['Content-Disposition'], 'attachment; filename="test.txt"')
