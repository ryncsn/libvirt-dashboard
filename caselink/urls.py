from django.conf.urls import url

from . import views

urlpatterns = [
    url(r'^$', views.index, name='index'),
    url(r'^a2m$', views.a2m, name='a2m'),
    url(r'^data$', views.data, name='data'),
    url(r'^manual/$', views.WorkItemList.as_view(), name='workitem'),
    url(r'^manual/(?P<pk>[a-zA-Z0-9\-]+)/$', views.WorkItemDetail.as_view(), name='workitem_detail'),
    url(r'^auto/$', views.AutoCaseList.as_view(), name='auto'),
    url(r'^auto/(?P<pk>[a-zA-Z0-9\-\._]+)/$', views.AutoCaseDetail.as_view(), name='auto_detail'),
    url(r'^link/$', views.LinkageList.as_view(), name='link'),
    url(r'^link/(?P<pk>[a-zA-Z0-9\-\._]+)/$', views.LinkageDetail.as_view(), name='link_detail'),
]
