from django.conf.urls import include, url
from django.contrib import admin

import registration.urls
import filebox.urls

urlpatterns = [
    url(r'^admin/', include(admin.site.urls)),

    url(r'^accounts/', include(registration.urls)),

    url(r'', include(filebox.urls, namespace='filebox')),
]
