from django.conf.urls import url

import filebox.views

urlpatterns = [
    url(r'^$', filebox.views.FileListView.as_view(), name='list'),
    url(r'^upload$', filebox.views.FileUploadView.as_view(), name='upload'),
    url(r'^download/(?P<pk>\d+)/(?P<filename>[^/\\"]+)', filebox.views.FileDownloadView.as_view(), name='download'),
    url(r'^delete/(?P<pk>\d+)$', filebox.views.FileDeleteView.as_view(), name='delete'),
]