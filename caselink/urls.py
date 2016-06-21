from django.conf.urls import url

from . import views

urlpatterns = [
    url(r'^$', views.index, name='index'),
    url(r'^a2m$', views.a2m, name='a2m'),
    url(r'^data$', views.data, name='data'),
    url(r'^update$', views.update, name='update'),
    url(r'^ignore$', views.ignore, name='ignore'),
    url(r'^workitems/$', views.WorkItemList.as_view(), name='workitem'),
    url(r'^workitems/(?P<pk>[a-zA-Z0-9\-]+)/$', views.WorkItemDetail.as_view(), name='workitem_detail'),
    url(r'^avocado/$', views.AvocadoCaseList.as_view(), name='avocado'),
    url(r'^avocado/(?P<pk>[a-zA-Z0-9\-\._]+)/$', views.AvocadoCaseDetail.as_view(), name='avocado'),
]
