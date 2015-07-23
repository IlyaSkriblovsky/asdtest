# -*- coding: utf-8 -*-

from django.forms import Form, FileField
from django.core.exceptions import ValidationError
from django.conf import settings

from filebox.models import FileMetaData


class FileUploadForm(Form):
    content = FileField(label=u'Файл')

    def __init__(self, user, *args, **kwargs):
        super(FileUploadForm, self).__init__(*args, **kwargs)

        self.user = user

    def clean(self):
        n_files = FileMetaData.objects.filter(user=self.user).count()
        if n_files >= settings.FILEBOX_MAX_FILES_PER_USER:
            raise ValidationError(
                u'Вы не можете загрузить более %(maxfiles)s файлов',
                params={'maxfiles': settings.FILEBOX_MAX_FILES_PER_USER}
            )

        return super(FileUploadForm, self).clean()

    def save(self):
        return FileMetaData.objects.create_with_content(
            user = self.user,
            filename = self.cleaned_data['content'].name,
            contentfile = self.cleaned_data['content'],
        )
