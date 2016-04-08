from django.conf.urls import url

from . import views

urlpatterns = [
    url(r'^$', views.index, name='index'),
    url(r'^a2m$', views.a2m, name='a2m'),
    url(r'^data$', views.data, name='data'),
    url(r'^update$', views.update, name='update'),
    url(r'^ignore$', views.ignore, name='ignore'),
]
