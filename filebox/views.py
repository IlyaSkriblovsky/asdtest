from django.views.generic import View
from django.views.generic.detail import SingleObjectMixin
from django.views.generic.edit import DeleteView, FormView
from django.views.generic.list import ListView
from django.core.urlresolvers import reverse_lazy
from django.contrib.auth.decorators import login_required
from django.http import HttpResponse
from django.core.servers.basehttp import FileWrapper

from filebox.models import FileMetaData
from filebox.forms import FileUploadForm


class LoginRequiredMixin(object):
    @classmethod
    def as_view(cls, *args, **kwargs):
        return login_required(super(LoginRequiredMixin, cls).as_view(*args, **kwargs))


class FileListView(LoginRequiredMixin, ListView):
    def get_queryset(self):
        return self.request.user.filemetadata_set.all()


class FileUploadView(LoginRequiredMixin, FormView):
    template_name = 'filebox/filemetadata_form.html'
    success_url = reverse_lazy('filebox:list')

    def get_form(self):
        return FileUploadForm(self.request.user, **self.get_form_kwargs())

    def form_valid(self, form):
        form.save()
        return super(FileUploadView, self).form_valid(form)


class FileDeleteView(LoginRequiredMixin, DeleteView):
    success_url = reverse_lazy('filebox:list')

    def get_queryset(self):
        return FileMetaData.objects.filter(user=self.request.user)


class FileDownloadView(SingleObjectMixin, View):
    model = FileMetaData

    def get(self, request, pk, filename):
        filemetadata = self.get_object()

        response = HttpResponse(FileWrapper(filemetadata.content.content), content_type='application/octet-stream')
        response['Content-Disposition'] = u'attachment; filename="{0}"'.format(filemetadata.filename)
        return response
