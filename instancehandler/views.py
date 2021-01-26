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

from django.shortcuts import render, redirect
from django.http import HttpResponse, JsonResponse
import yaml
import json
import logging
from lib.osm.osmclient.clientv2 import Client
from lib.osm.osm_rdcl_parser import OsmParser
import authosm.utils as osmutils
from sf_t3d.decorators import login_required

logging.basicConfig(level=logging.DEBUG)
log = logging.getLogger('instancehandler/view.py')


@login_required
def get_list(request, type=None):
    user = osmutils.get_user(request)
    project_id = user.project_id
    client = Client()
    result = {'type': type, 'project_id': project_id}
    if "OSM_ERROR" in request.session:
        result['alert_error'] = request.session["OSM_ERROR"]
        del request.session["OSM_ERROR"]
    raw_content_types = request.META.get('HTTP_ACCEPT', '*/*').split(',')
    if 'application/json' not in raw_content_types:
        return __response_handler(request, result, 'instance_list.html')
    instance_list = None
    if type == 'ns':
        instance_list = client.ns_list(user.get_token())
    elif type == 'vnf':
        instance_list = client.vnf_list(user.get_token())
    elif type == 'pdu':
        instance_list = client.pdu_list(user.get_token())
    elif type == 'nsi':
        instance_list = client.nsi_list(user.get_token())

    result['instances'] = instance_list['data'] if instance_list and instance_list['error'] is False else []

    return __response_handler(request, result, 'instance_list.html')

@login_required
def create(request, type=None):
    result = {}
    config_vim_account_id = {}
    config_wim_account_id = {}
    user = osmutils.get_user(request)
    client = Client()

    def get_vim_account_id(vim_account):
        if config_vim_account_id.get(vim_account):
            return config_vim_account_id[vim_account]
        result_client = client.vim_list(user.get_token())
        vim_list = result_client['data'] if result_client and result_client['error'] is False else []
        if vim_list is None or len(vim_list) == 0:
            raise ValueError("cannot find vim account '{}'".format(vim_account))
        for vim in vim_list:
            if vim_account == vim['name']:
                config_vim_account_id[vim_account] = vim['uuid']
                return vim['uuid']
    
    def get_wim_account_id(wim_account):

        if config_wim_account_id.get(wim_account):
            return config_wim_account_id[wim_account]
        result_client = client.wim_list(user.get_token())
        wim_list = result_client['data'] if result_client and result_client['error'] is False else []
        if wim_list is None or len(wim_list) == 0:
            raise ValueError("cannot find wim account '{}'".format(wim_account))
        for wim in wim_list:
            if wim_account == wim['name']:
                config_wim_account_id[wim_account] = wim['uuid']
                return wim['uuid']


    if type == 'ns':
        try:

            ns_data = {
                "nsName": request.POST.get('nsName', 'WithoutName'),
                "nsDescription": request.POST.get('nsDescription', ''),
                "nsdId": request.POST.get('nsdId', ''),
                "vimAccountId": request.POST.get('vimAccountId', ''),
            }
            ns_data["ssh_keys"] = []
            if 'ssh_key' in request.POST and request.POST.get('ssh_key') != '':
                ns_data["ssh_keys"].append(request.POST.get('ssh_key'))
            ssh_key_files = request.FILES.getlist('ssh_key_files')
            for ssh_key_file in ssh_key_files:
                ssh_key = ''
                for line in ssh_key_file:
                    ssh_key = ssh_key + line.decode()
                ns_data["ssh_keys"].append(ssh_key)
            

            config_file = request.FILES.get('config_file')
            
            if config_file is not None:
                config = ''
                for line in config_file:
                    config = config + line.decode()
                ns_config = yaml.load(config)
            elif 'config' in request.POST and request.POST.get('config') != '':
                ns_config = yaml.load(request.POST.get('config'))
            else:
                ns_config = None
            
           
            if ns_config is not None:
                if isinstance(ns_config, dict):
                    if "vim-network-name" in ns_config:
                        ns_config["vld"] = ns_config.pop("vim-network-name")
                    if "vld" in ns_config:
                        for vld in ns_config["vld"]:
                            if vld.get("vim-network-name"):
                                if isinstance(vld["vim-network-name"], dict):
                                    vim_network_name_dict = {}
                                    for vim_account, vim_net in list(vld["vim-network-name"].items()):
                                        vim_network_name_dict[get_vim_account_id(vim_account)] = vim_net
                                    vld["vim-network-name"] = vim_network_name_dict
                            if "wim_account" in vld and vld["wim_account"] is not None:
                                vld["wimAccountId"] = get_wim_account_id(vld.pop("wim_account"))
                        ns_data["vld"] = ns_config["vld"]
                    if "vnf" in ns_config:
                        for vnf in ns_config["vnf"]:
                            if vnf.get("vim_account"):
                                vnf["vimAccountId"] = get_vim_account_id(vnf.pop("vim_account"))
                        ns_data["vnf"] = ns_config["vnf"]

                    if "additionalParamsForNs" in ns_config:
                        ns_data["additionalParamsForNs"] = ns_config.pop("additionalParamsForNs")
                        if not isinstance(ns_data["additionalParamsForNs"], dict):
                            raise ValueError("Error  'additionalParamsForNs' must be a dictionary")
                    if "additionalParamsForVnf" in ns_config:
                        ns_data["additionalParamsForVnf"] = ns_config.pop("additionalParamsForVnf")
                        if not isinstance(ns_data["additionalParamsForVnf"], list):
                            raise ValueError("Error  'additionalParamsForVnf' must be a list")
                        for additional_param_vnf in ns_data["additionalParamsForVnf"]:
                            if not isinstance(additional_param_vnf, dict):
                                raise ValueError("Error  'additionalParamsForVnf' items must be dictionaries")
                            if not additional_param_vnf.get("member-vnf-index"):
                                raise ValueError("Error  'additionalParamsForVnf' items must contain "
                                                "'member-vnf-index'")
                            if not additional_param_vnf.get("additionalParams"):
                                raise ValueError("Error  'additionalParamsForVnf' items must contain "
                                                "'additionalParams'")
                    if "wim_account" in ns_config:
                        wim_account = ns_config.pop("wim_account")
                        if wim_account is not None:
                            ns_data['wimAccountId'] = get_wim_account_id(wim_account)

        except Exception as e:
            return __response_handler(request, {'status': 400, 'code': 'BAD_REQUEST', 'detail': e.message} , url=None, status=400)
        result = client.ns_create(user.get_token(), ns_data)
        
        if result['error']:
            return __response_handler(request, result['data'], url=None,
                                  status=result['data']['status'] if 'status' in result['data'] else 500)
        else:
            return __response_handler(request, {}, url=None, status=200)

    elif type == 'nsi':
        try:
            nsi_data = {
                "nsiName": request.POST.get('nsiName', 'WithoutName'),
                "nsiDescription": request.POST.get('nsiDescription', ''),
                "nstId": request.POST.get('nstId', ''),
                "vimAccountId": request.POST.get('vimAccountId', ''),
            }
            
            nsi_data["ssh_keys"] = []
            if 'ssh_key' in request.POST and request.POST.get('ssh_key') != '':
                nsi_data["ssh_keys"].append(request.POST.get('ssh_key'))
            ssh_key_files = request.FILES.getlist('ssh_key_files')
            for ssh_key_file in ssh_key_files:
                ssh_key = ''
                for line in ssh_key_file:
                    ssh_key = ssh_key + line.decode()
                nsi_data["ssh_keys"].append(ssh_key)
            nsi_data["ssh_keys"] = ','.join(nsi_data["ssh_keys"])
          
            config_file = request.FILES.get('config_file')
            
            if config_file is not None:
                config = ''
                for line in config_file:
                    config = config + line.decode()
                nsi_config = yaml.load(config)
            elif 'config' in request.POST and request.POST.get('config') != '':
                nsi_config = yaml.load(request.POST.get('config'))
            else:
                nsi_config = None
            
            if nsi_config is not None:
                if "netslice-vld" in nsi_config:
                    for vld in nsi_config["netslice-vld"]:
                        if vld.get("vim-network-name"):
                            if isinstance(vld["vim-network-name"], dict):
                                vim_network_name_dict = {}
                                for vim_account, vim_net in list(vld["vim-network-name"].items()):
                                    vim_network_name_dict[get_vim_account_id(vim_account)] = vim_net
                                vld["vim-network-name"] = vim_network_name_dict
                    nsi_data["netslice-vld"] = nsi_config["netslice-vld"]
                if "netslice-subnet" in nsi_config:
                    for nssubnet in nsi_config["netslice-subnet"]:
                        if "vld" in nssubnet:
                            for vld in nssubnet["vld"]:
                                if vld.get("vim-network-name"):
                                    if isinstance(vld["vim-network-name"], dict):
                                        vim_network_name_dict = {}
                                        for vim_account, vim_net in list(vld["vim-network-name"].items()):
                                            vim_network_name_dict[get_vim_account_id(vim_account)] = vim_net
                                        vld["vim-network-name"] = vim_network_name_dict
                        if "vnf" in nssubnet:
                            for vnf in nsi_config["vnf"]:
                                if vnf.get("vim_account"):
                                    vnf["vimAccountId"] = get_vim_account_id(vnf.pop("vim_account"))
                    nsi_data["netslice-subnet"] = nsi_config["netslice-subnet"]
                if "additionalParamsForNsi" in nsi_config:
                    nsi_data["additionalParamsForNsi"] = nsi_config.pop("additionalParamsForNsi")
                    if not isinstance(nsi_data["additionalParamsForNsi"], dict):
                        raise ValueError("Error at 'additionalParamsForNsi' must be a dictionary")
                if "additionalParamsForSubnet" in nsi_config:
                    nsi_data["additionalParamsForSubnet"] = nsi_config.pop("additionalParamsForSubnet")
                    if not isinstance(nsi_data["additionalParamsForSubnet"], list):
                        raise ValueError("Error 'additionalParamsForSubnet' must be a list")
                    for additional_param_subnet in nsi_data["additionalParamsForSubnet"]:
                        if not isinstance(additional_param_subnet, dict):
                            raise ValueError("Error 'additionalParamsForSubnet' items must be dictionaries")
                        if not additional_param_subnet.get("id"):
                            raise ValueError("Error 'additionalParamsForSubnet' items must contain subnet 'id'")
                        if not additional_param_subnet.get("additionalParamsForNs") and\
                                not additional_param_subnet.get("additionalParamsForVnf"):
                            raise ValueError("Error 'additionalParamsForSubnet' items must contain "
                                            "'additionalParamsForNs' and/or 'additionalParamsForVnf'")
        except Exception as e:
            return __response_handler(request, {'status': 400, 'code': 'BAD_REQUEST', 'detail': e.message} , url=None, status=400)

        result = client.nsi_create(user.get_token(), nsi_data)
        if result['error']:
            return __response_handler(request, result['data'], url=None,
                                  status=result['data']['status'] if 'status' in result['data'] else 500)
        else:
            return __response_handler(request, {}, url=None, status=200)

    elif type == 'pdu':
        interface_param_name = request.POST.getlist('interfaces_name')
        interface_param_ip = request.POST.getlist('interfaces_ip')
        interface_param_mgmt = request.POST.getlist('interfaces_mgmt')
        interface_param_netname = request.POST.getlist('interfaces_vimnetname')

        pdu_payload = {
            "name": request.POST.get('name'),
            "type": request.POST.get('pdu_type'),
            "vim_accounts": request.POST.getlist('pdu_vim_accounts'),
            "description": request.POST.get('description'),
            "interfaces": []
        }
        for i in (0,len(interface_param_name)-1):
            pdu_payload['interfaces'].append({
                'name': interface_param_name[i],
                'mgmt': True if interface_param_mgmt[i] == 'true' else False,
                'ip-address': interface_param_ip[i],
                'vim-network-name': interface_param_netname[i]
            })
        result = client.pdu_create(user.get_token(), pdu_payload)
        if result['error']:
            return __response_handler(request, result['data'], url=None,
                                  status=result['data']['status'] if 'status' in result['data'] else 500)
        else:
            return __response_handler(request, {}, url=None, status=200)

@login_required
def ns_operations(request, instance_id=None, type=None):
    user = osmutils.get_user(request)
    project_id = user.project_id

    result = {'type': type, 'project_id': project_id, 'instance_id': instance_id}
    raw_content_types = request.META.get('HTTP_ACCEPT', '*/*').split(',')
    if 'application/json' not in raw_content_types:
        return __response_handler(request, result, 'instance_operations_list.html')
    client = Client()
    if type == 'ns':
        op_list = client.ns_op_list(user.get_token(), instance_id)
    elif type == 'nsi':
        op_list = client.nsi_op_list(user.get_token(), instance_id)
    result['operations'] = op_list['data'] if op_list and op_list['error'] is False else []

    return __response_handler(request, result, 'instance_operations_list.html')

@login_required
def ns_operation(request, op_id, instance_id=None, type=None):
    user = osmutils.get_user(request)
    client = Client()
    result = client.ns_op(user.get_token(), op_id)
    return __response_handler(request, result['data'])


@login_required
def action(request, instance_id=None, type=None):
    user = osmutils.get_user(request)
    client = Client()
    # result = client.ns_action(instance_id, action_payload)
    primitive_param_keys = request.POST.getlist('primitive_params_name')
    primitive_param_value = request.POST.getlist('primitive_params_value')
    action_payload = {
        "vnf_member_index": request.POST.get('vnf_member_index'),
        "primitive": request.POST.get('primitive'),
        "primitive_params": {k: v for k, v in zip(primitive_param_keys, primitive_param_value) if len(k) > 0}
    }

    result = client.ns_action(user.get_token(), instance_id, action_payload)
    if result['error']:
        return __response_handler(request, result['data'], url=None,
                                  status=result['data']['status'] if 'status' in result['data'] else 500)
    else:
        return __response_handler(request, {}, url=None, status=200)


@login_required
def delete(request, instance_id=None, type=None):
    force = bool(request.GET.get('force', False))
    result = {}
    user = osmutils.get_user(request)
    client = Client()
    if type == 'ns':
        result = client.ns_delete(user.get_token(), instance_id, force)
    elif type == 'pdu':
        result = client.pdu_delete(user.get_token(), instance_id)
    elif type == 'nsi':
        result = client.nsi_delete(user.get_token(), instance_id, force)

    if result['error']:
        return __response_handler(request, result['data'], url=None,
                                  status=result['data']['status'] if 'status' in result['data'] else 500)
    else:
        return __response_handler(request, {}, url=None, status=200)

@login_required
def show_topology(request, instance_id=None, type=None):
    user = osmutils.get_user(request)
    project_id = user.project_id
    raw_content_types = request.META.get('HTTP_ACCEPT', '*/*').split(',')
    if 'application/json' in raw_content_types:
        client = Client()
        nsr_object = {'nsr': {}, 'vnfr': {}, 'vnfd': {}}
        if type == 'ns':

            nsr_resp = client.ns_get(user.get_token(), instance_id)
            nsr_object['nsr'] = nsr_resp['data']
            if 'constituent-vnfr-ref' in nsr_object['nsr'] :
                for vnfr_id in nsr_object['nsr']['constituent-vnfr-ref']:
                    vnfr_resp = client.vnf_get(user.get_token(), vnfr_id)
                    vnfr = vnfr_resp['data']
                    nsr_object['vnfr'][vnfr['id']] = vnfr
                    if vnfr['vnfd-id'] not in nsr_object['vnfd']:
                        vnfd_resp = client.vnfd_get(user.get_token(), vnfr['vnfd-id'])
                        nsr_object['vnfd'][vnfr['vnfd-id']] = vnfd_resp['vnfd:vnfd-catalog']['vnfd'][0]

        test = OsmParser()

        result = test.nsr_to_graph(nsr_object)
        return __response_handler(request, result)
    else:
        result = {'type': type, 'project_id': project_id, 'instance_id': instance_id}
        return __response_handler(request, result, 'instance_topology_view.html')


@login_required
def show(request, instance_id=None, type=None):
    # result = {}
    user = osmutils.get_user(request)
    project_id = user.project_id
    client = Client()
    if type == 'ns':
        result = client.ns_get(user.get_token(), instance_id)
    elif type == 'vnf':
        result = client.vnf_get(user.get_token(), instance_id)
    elif type == 'pdu':
        result = client.pdu_get(user.get_token(), instance_id)
    elif type == 'nsi':
        result = client.nsi_get(user.get_token(), instance_id)

    return __response_handler(request, result)


@login_required
def export_metric(request, instance_id=None, type=None):
    metric_data = request.POST.dict()
    user = osmutils.get_user(request)
    project_id = user.project_id
    client = Client()
    keys = ["collection_period",
            "vnf_member_index",
            "metric_name",
            "correlation_id",
            "vdu_name",
            "collection_unit"]
    metric_data = dict(filter(lambda i: i[0] in keys and len(i[1]) > 0, metric_data.items()))

    result = client.ns_metric_export(user.get_token(), instance_id, metric_data)

    if result['error']:
        return __response_handler(request, result['data'], url=None,
                                  status=result['data']['status'] if 'status' in result['data'] else 500)
    else:
        return __response_handler(request, {}, url=None, status=200)


@login_required
def create_alarm(request, instance_id=None, type=None):
    metric_data = request.POST.dict()
    user = osmutils.get_user(request)
    project_id = user.project_id
    client = Client()

    keys = ["threshold_value",
            "vnf_member_index",
            "metric_name",
            "vdu_name",
            "alarm_name",
            "correlation_id",
            "statistic",
            "operation",
            "severity"]
    metric_data = dict(filter(lambda i: i[0] in keys and len(i[1]) > 0, metric_data.items()))

    result = client.ns_alarm_create(user.get_token(), instance_id, metric_data)
    if result['error']:
        return __response_handler(request, result['data'], url=None,
                                  status=result['data']['status'] if 'status' in result['data'] else 500)
    else:
        return __response_handler(request, {}, url=None, status=200)


def __response_handler(request, data_res, url=None, to_redirect=None, *args, **kwargs):
    raw_content_types = request.META.get('HTTP_ACCEPT', '*/*').split(',')
    if not to_redirect and ('application/json' in raw_content_types or url is None):
        return HttpResponse(json.dumps(data_res), content_type="application/json", *args, **kwargs)
    elif to_redirect:
        return redirect(url, *args, **kwargs)
    else:
        return render(request, url, data_res)
