from django.contrib import admin

from filebox.models import FileMetaData, FileContent

# Register your models here.
admin.site.register(FileMetaData)
admin.site.register(FileContent)
