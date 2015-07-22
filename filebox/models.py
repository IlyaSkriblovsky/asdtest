import hashlib

from django.db import models
from django.contrib.auth.models import User
from django.db.models.signals import post_delete
from django.dispatch import receiver


def _sha1_of_file(file):
    hash = hashlib.sha1()
    for chunk in file.chunks():
        hash.update(chunk)
    return hash.hexdigest()


class FileContentManager(models.Manager):
    def find_existing_or_create(self, file):
        sha1 = _sha1_of_file(file)

        # not iterating `file` via chunks() since it is usually InMemoryUploadedFile
        file.seek(0)
        content = file.read()

        for existing in self.model.objects.filter(sha1=sha1):
            if existing.content.size != file.size:
                continue

            equals = True
            pos = 0
            for chunk in existing.content.chunks():
                if chunk != content[pos : pos + len(chunk)]:
                    equals = False
                    break
                pos += len(chunk)

            if equals:
                existing.incref()
                return existing

        return self.create(content=file, sha1=sha1, refcount=1)


class FileContent(models.Model):
    objects = FileContentManager()

    content = models.FileField()
    sha1 = models.CharField(max_length=40, db_index=True)
    refcount = models.IntegerField(default=1)

    def __unicode__(self):
        return u'{0} ({1} bytes, refs={2})'.format(self.sha1[:10], self.content.size, self.refcount)

    def incref(self, nrefs=1, commit=True):
        self.refcount += nrefs
        if commit:
            self.save(update_fields=['refcount'])

    def decref(self, nrefs=1, commit=True):
        self.refcount -= nrefs
        if self.refcount > 0:
            if commit:
                self.save(update_fields=['refcount'])
        else:
            self.content.delete()
            self.delete()

    def save(self, *args, **kwargs):
        if not self.sha1:
            self.sha1 = _sha1_of_file(self.content)
        return super(FileContent, self).save(*args, **kwargs)


class FileMetaDataManager(models.Manager):
    def create_with_content(self, contentfile, **kwargs):
        filecontent = FileContent.objects.find_existing_or_create(contentfile)
        return super(FileMetaDataManager, self).create(content=filecontent, **kwargs)

class FileMetaData(models.Model):
    class Meta:
        ordering = [ '-uploaded_at' ]
        index_together = [
            [ 'user', 'uploaded_at' ]
        ]

    objects = FileMetaDataManager()

    user = models.ForeignKey(User, db_index=True)
    filename = models.CharField(max_length=256)
    uploaded_at = models.DateTimeField(auto_now_add=True, null=True)
    content = models.ForeignKey(FileContent)

    def __unicode__(self):
        return u'{0} (user: {1})'.format(self.filename, self.user)



@receiver(post_delete, sender=FileMetaData, dispatch_uid='unref_filecontent')
def unref_filecontent(sender, instance, using, **kwargs):
    instance.content.decref()
