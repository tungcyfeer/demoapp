#
#   Copyright 2018 CNIT - Consorzio Nazionale Interuniversitario per le Telecomunicazioni
#
#   Licensed under the Apache License, Version 2.0 (the "License");
#   you may not use this file except in compliance with the License.
#   You may obtain a copy of the License at
#
#       http://www.apache.org/licenses/LICENSE-2.0
#
#   Unless required by applicable law or agreed to in writing, software
#   distributed under the License is distributed on an  BASIS,
#   WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
#   See the License for the specific language governing permissions and
#   limitations under the License.
#

from django.conf.urls import url
from instancehandler import views

urlpatterns = [
    url(r'^(?P<type>[ns|vnf|pdu|nsi]+)/list/', views.get_list, name='list'),
    url(r'^(?P<type>[ns|pdu|nsi]+)/create/', views.create, name='create'),
    url(r'^(?P<type>[ns|pdu|nsi]+)/(?P<instance_id>[0-9a-z-]+)/delete$', views.delete, name='delete'),
    url(r'^(?P<type>[ns|vnf]+)/(?P<instance_id>[0-9a-z-]+)/topology', views.show_topology, name='show_topology'),
    url(r'^(?P<type>[ns|vnf]+)/(?P<instance_id>[0-9a-z-]+)/action$', views.action, name='action'),
    url(r'^(?P<type>[ns|vnf|nsi]+)/(?P<instance_id>[0-9a-z-]+)/operation$', views.ns_operations, name='ns_operations'),
    url(r'^(?P<type>[ns|vnf]+)/(?P<instance_id>[0-9a-z-]+)/operation/(?P<op_id>[0-9a-z-]+)', views.ns_operation, name='ns_operation'),
    url(r'^(?P<type>[ns|vnf]+)/(?P<instance_id>[0-9a-z-]+)/monitoring/alarm$', views.create_alarm, name='ns_create_alarm'),
    url(r'^(?P<type>[ns|vnf]+)/(?P<instance_id>[0-9a-z-]+)/monitoring/metric$', views.export_metric, name='ns_export_metric'),
    url(r'^(?P<type>[ns|vnf|pdu|nsi]+)/(?P<instance_id>[0-9a-z-]+)', views.show, name='show'),

]
