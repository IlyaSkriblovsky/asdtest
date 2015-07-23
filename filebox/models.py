import hashlib
import logging

from django.db import models
from django.contrib.auth.models import User
from django.db.models.signals import pre_delete, post_delete, post_save
from django.dispatch import receiver

logger = logging.getLogger('filebox.models')


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
        """
        Returns True if filecontent was deleted since it's not referenced anymore
        Returns False if filecontent has more references to it
        """
        self.refcount -= nrefs
        if self.refcount > 0:
            if commit:
                self.save(update_fields=['refcount'])
            return False
        else:
            self.content.delete()
            self.delete()
            return True

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
        return u'"{0}" (user: {1})'.format(self.filename, self.user)



@receiver(post_save, sender=FileMetaData, dispatch_uid='on_filemetadata_create')
def on_filemetadata_create(sender, instance, created, **kwargs):
    if created:
        if instance.content.refcount > 1:
            log_msg = 'User "%(user)s" uploaded file "%(filename)s", referencing already existing filecontent %(filecontent)s'
        else:
            log_msg = 'User "%(user)s" uploaded file "%(filename)s", adding new filecontent %(filecontent)s'
        logger.info(log_msg, {'user': instance.user, 'filename': instance.filename, 'filecontent': instance.content })

@receiver(post_delete, sender=FileMetaData, dispatch_uid='on_filemetadata_delete')
def on_filemetadata_delete(sender, instance, **kwargs):
    filecontent_str = unicode(instance.content)

    content_deleted = instance.content.decref()

    if content_deleted:
        log_msg = 'User "%(user)s" deleted file "%(filename)s", deleting filecontent %(filecontent)s'
    else:
        log_msg = 'User "%(user)s" deleted file "%(filename)s", keeping filecontent %(filecontent)s'
    logger.info(log_msg, { 'user': instance.user, 'filename': instance.filename, 'filecontent': filecontent_str })
