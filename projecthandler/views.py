#
#   Copyright 2017 CNIT - Consorzio Nazionale Interuniversitario per le Telecomunicazioni
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

import json
import logging

import yaml
from sf_t3d.decorators import login_required
from django.http import HttpResponse, JsonResponse
from django.shortcuts import render, redirect

from authosm.exceptions import OSMAuthException
from lib.util import Util
from lib.osm.osmclient.clientv2 import Client
import authosm.utils as osmutils


logging.basicConfig(level=logging.DEBUG)
log = logging.getLogger('projecthandler/view.py')


@login_required
def home(request):
    return render(request, 'home.html', {})


@login_required
def create_new_project(request):
    if request.method == 'POST':
        user = osmutils.get_user(request)
        client = Client()
        new_project_dict = request.POST.dict()
        keys = ["name", "domain_name"]
        project_data = dict(filter(lambda i: i[0] in keys and len(i[1]) > 0, new_project_dict.items()))
        result = client.project_create(user.get_token(), project_data)
        if isinstance(result, dict) and 'error' in result and result['error']:
            return __response_handler(request, result['data'], url=None,
                                      status=result['data']['status'] if 'status' in result['data'] else 500)
        else:
            return __response_handler(request, {}, url=None, status=200)


@login_required
def user_projects(request):
    user = osmutils.get_user(request)
    client = Client()
    result = client.project_list(user.get_token())
    return __response_handler(request, {
        'projects': result['data'] if result and result['error'] is False else [],
    },'projectlist.html')


@login_required
def user_domains(request):
    user = osmutils.get_user(request)
    client = Client()
    result = client.get_domains(user.get_token())
    if result and result['error'] is False:
        domains = []
        if result['data'] and result['data']['user_domain_name']:
            domain_names = result['data']['user_domain_name'].split(',')
            domains.extend(x for x in domain_names if x not in domains)
        if result['data'] and result['data']['project_domain_name']:
            domain_names = result['data']['project_domain_name'].split(',')
            domains.extend(x for x in domain_names if x not in domains)

        return __response_handler(request, {'domains': domains})
    return __response_handler(request, {'domains': []})


@login_required
def open_project(request):
    user = osmutils.get_user(request)
    project_id = user.project_id
    try:

        client = Client()
        ##TODO change with adhoc api call
        prj = client.project_get(user.get_token(), project_id)
        nsd = client.nsd_list(user.get_token())
        vnfd = client.vnfd_list(user.get_token())
        ns = client.ns_list(user.get_token())
        vnf = client.vnf_list(user.get_token())
        proj_data_admin =  prj['data']['_admin'] if prj and prj['error'] is False and prj['data'] and  prj['data']['_admin'] else None
        project_overview = {
            'owner': user.username,
            'name': user.project_name,
            'updated_date': proj_data_admin['modified'] if proj_data_admin else '-',
            'created_date': proj_data_admin['created'] if proj_data_admin else '-',

            'type': 'osm',
            'nsd': len(nsd['data']) if nsd and nsd['error'] is False else 0,
            'vnfd': len(vnfd['data']) if vnfd and vnfd['error'] is False else 0,
            'ns': len(ns['data']) if ns and ns['error'] is False else 0,
            'vnf': len(vnf['data']) if vnf and vnf['error'] is False else 0,
        }
        return render(request, 'osm/osm_project_details.html',
                      {'project_overview': project_overview, 'project_id': project_id})

    except Exception as e:
        return render(request, 'error.html', {'error_msg': 'Error open project! Please retry.'})


@login_required
def delete_project(request, project_id):
    user = osmutils.get_user(request)

    client = Client()
    result = client.project_delete(user.get_token(), project_id)
    if isinstance(result, dict) and 'error' in result and result['error']:
        return __response_handler(request, result['data'], url=None,
                                  status=result['data']['status'] if 'status' in result['data'] else 500)
    else:
        return __response_handler(request, {}, url=None, status=200)


@login_required
def switch_project(request, project_id):
    user = osmutils.get_user(request)
    user.switch_project(project_id)
    return redirect('projects:open_project')


@login_required
def edit_project(request, project_id):
    if request.method == 'POST':
        user = osmutils.get_user(request)
        client = Client()
        project_dict = request.POST.dict()
        keys = ["name"]
        project_data = dict(filter(lambda i: i[0] in keys and len(i[1]) > 0, project_dict.items()))
        result = client.project_edit(user.get_token(), project_id, project_data)
        if isinstance(result, dict) and 'error' in result and result['error']:
            return __response_handler(request, result['data'], url=None,
                                      status=result['data']['status'] if 'status' in result['data'] else 500)
        else:
            return __response_handler(request, {}, url=None, status=200)


def __response_handler(request, data_res, url=None, to_redirect=None, *args, **kwargs):
    raw_content_types = request.META.get('HTTP_ACCEPT', '*/*').split(',')
    if 'application/json' in raw_content_types or url is None:
        return HttpResponse(json.dumps(data_res), content_type="application/json", *args, **kwargs)
    elif to_redirect:
        return redirect(url, *args, **kwargs)
    else:
        return render(request, url, data_res)
