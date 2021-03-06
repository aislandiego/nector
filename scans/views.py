from django.shortcuts import render, get_object_or_404

from django.http import HttpResponseRedirect
from django.http import HttpResponse
from django.template.context_processors import csrf
from django.template import loader

from forms import ScansForm

from models import ScanType

import nmap

import json

'''
    Useful nmap scans we can use as defaults (todo):
        1. Scan for UDP DDOS reflectors:
            nmap -sU -A -PN -n -pU:19,53,123,161 -script=ntp-monlist,dns-recursion,snmp-sysdescr 192.168.1.0/24
        2. Get HTTP headers of web services:
            nmap --script=http-headers 192.168.1.0/24
        3. Heartbleed Testing:
            nmap -sV -p 443 --script=ssl-heartbleed 192.168.1.0/24
        4. IP Information:
            nmap --script=asn-query,whois,ip-geolocation-maxmind 192.168.1.0/24
        5. Scan 100 most common ports (Fast):
            nmap -F 192.168.1.1
'''


def get_nmap_command(request, context):
    """TODO: Add results of the live scan to context. Display on page."""

    scan_name = context['scan_name']
    host_address = context['host_address']
    ports = context['ports']
    scan_options = context['scan_options']

    args = ''

    for opt in scan_options:
        print opt
        if 'version_detection' in opt:
            args += '-sV '
        if 'os_and_services' in opt:
            args += '-A '
        if 'fast' in opt:
            args += '-F '
        if 'no_ping' in opt:
            args += '-Pn '

    if ports:
        tmp_ports = []
        if ',' in ports:
            args += '-p'

            tmp_ports = ports.split(',')

            str_port_list = ''

            for p in tmp_ports:
                p = p.strip()
                try:
                    if int(p) > 0 and int(p) <= 65535:
                        str_port_list += str(p) + ','
                    else:
                        print 'Invalid port %s' % p
                        return None
                except:
                    print 'Invalid port %s' % p
                    return None

            args += str_port_list

        elif '-' in ports:
            args += '-p'

            tmp_ports = ports.split('-')

            is_valid_range = True
            for p in tmp_ports:
                p = p.strip()
                try:
                    if int(p) > 0 and int(p) <= 65535:
                        print 'Good'
                    else:
                        is_valid_range = False
                except:
                    print 'Invalid port %s' % p
                    return None

            if is_valid_range:
                args += ports

        elif ' ' in ports:
            args += '-p'

            tmp_ports = ports.split(' ')

            str_port_list = ''

            for p in tmp_ports:
                p = p.strip()
                try:
                    if int(p) > 0 and int(p) <= 65535:
                        str_port_list += str(p) + ','
                    else:
                        print 'Invalid port %s' % p
                        return None
                except:
                    print 'Invalid port %s' % p
                    return None

            args += str_port_list

        else:
            p = ports.strip()
            try:
                if int(p) > 0 and int(p) <= 65535:
                    args += '-p'
                    args += p
            except:
                print 'Invalid port %s' % p
                return None

    return host_address, args


def live_scan(request, context):

    nm = nmap.PortScanner()

    host_address, args = get_nmap_command(request, context)

    try:
        nm.scan(hosts=host_address, arguments=args)

        nmap_output = [nm.command_line()]

        for host in nm.all_hosts():
            nmap_output.append('-------------------------------')
            nmap_output.append('Host : %s (%s)' % (host, nm[host].hostname()))
            nmap_output.append('State : %s' % nm[host].state())
            for proto in nm[host].all_protocols():
                nmap_output.append('~~~~~~~~')
                nmap_output.append('Protocol : %s' % proto)
                lport = nm[host][proto].keys()
                lport.sort()
                for port in lport:
                    nmap_output.append('port : %s | state : %s | name : %s' % \
                        (port,
                         nm[host][proto][port]['state'],
                         nm[host][proto][port]['product'] + ' ' + \
                         nm[host][proto][port]['version'] + ' ' + \
                         nm[host][proto][port]['extrainfo']))

        context['nmap_output'] = nmap_output
    except Exception as e:
        print e
        context['nmap_output'] = ['Something went wrong!']

    return render(request, 'scans/scans.html', context)


def delete_scan(request, context):
    if request.POST:
        if request.user.is_authenticated():
            if 'selected_scan_name' in request.POST:
                scan_to_delete = request.POST['selected_scan_name']
                user = request.user
                try:
                    scan_inst = ScanType.objects.get(scan_name=scan_to_delete)
                    scan_inst.delete()
                except Exception as e:
                    print '%s' % e
    return render(request, 'scans/scans.html', context)


def edit_scan(request):

    context = {}

    scan_name = request.POST.get("selected_scan_name")

    scan_obj = get_object_or_404(ScanType, scan_name=scan_name, user=request.user)

    scan_options = []

    dirty_scan_options = scan_obj.scan_options

    if dirty_scan_options:
        if 'version_detection' in dirty_scan_options:
            scan_options.append('version_detection')
        if 'os_and_services' in dirty_scan_options:
            scan_options.append('os_and_services')
        if 'fast' in dirty_scan_options:
            scan_options.append('fast')
        if 'no_ping' in dirty_scan_options:
            scan_options.append('no_ping')

    scan_obj.scan_options = scan_options

    form = ScansForm(instance=scan_obj)

    if request.user.is_authenticated():
        saved_scans = ScanType.objects.filter(user=request.user)
        context['saved_scans'] = saved_scans

    context.update(csrf(request))
    context['form'] = form
    return render(request, 'scans/scans.html', context)


def index(request):
    '''
    Default scanning page.
    If a POST request was made to get here, then our form was submitted,
    so display the results of the query made.
    Otherwise, just display the form.
    '''

    context = {}

    if request.user.is_authenticated():
        saved_scans = ScanType.objects.filter(user=request.user)
        context['saved_scans'] = saved_scans

    live_scanning = False


    if request.POST.get("live_scan"):
        # User pressed Live Scan button.
        live_scanning = True

    if request.method == "POST":

        if request.POST.get("btn_edit_scan"):
            print 'edit'
            return edit_scan(request)

        elif request.POST.get("btn_live_scan"):
            print 'live'
            scan_name = request.POST.get("selected_scan_name")

            scan_obj = get_object_or_404(ScanType, scan_name=scan_name, user=request.user)

            scan_name = scan_obj.scan_name
            host_address = scan_obj.host_address
            ports = scan_obj.ports
            scan_options = []

            dirty_scan_options = scan_obj.scan_options

            if dirty_scan_options:
                if 'version_detection' in dirty_scan_options:
                    scan_options.append('version_detection')
                if 'os_and_services' in dirty_scan_options:
                    scan_options.append('os_and_services')
                if 'fast' in dirty_scan_options:
                    scan_options.append('fast')
                if 'no_ping' in dirty_scan_options:
                    scan_options.append('no_ping')


            # Append important info to context.

            context.update(csrf(request))
            context['scan_name'] = scan_name
            context['host_address'] = host_address
            context['ports'] = ports
            context['scan_options'] = scan_options

            if request.user.is_authenticated():
                saved_scans = ScanType.objects.filter(user=request.user)
                context['saved_scans'] = saved_scans

            scan_obj.scan_options = scan_options

            context.update(csrf(request))
            form = ScansForm(instance=scan_obj)
            context['form'] = form
            return live_scan(request, context)

        elif request.POST.get("btn_delete_scan"):
            print 'delete'
            context = {}

            if request.user.is_authenticated():
                saved_scans = ScanType.objects.filter(user=request.user)
                context['saved_scans'] = saved_scans

            context.update(csrf(request))
            form = ScansForm()
            context['form'] = form

            return delete_scan(request, context)

        else:

            # Get form information.
            print 'else'

            form = ScansForm(request.POST)

            print request.POST

            if form.is_valid():

                scan_name = form.cleaned_data['scan_name']
                host_address = form.cleaned_data['host_address']
                ports = form.cleaned_data['ports']
                scan_options = form.cleaned_data['scan_options'].split(',')

                # Append important info to context.

                context.update(csrf(request))
                context['scan_name'] = scan_name
                context['host_address'] = host_address
                context['ports'] = ports
                context['scan_options'] = scan_options
                context['form'] = form

                '''
                existing_scan_instance = None
                if ScanType.objects.filter(scan_name=scan_name).exists():
                    existing_scan_instance = get_object_or_404(ScanType, scan_name=scan_name)
                '''

                if live_scanning:
                    # Perform live nmap scan.
                    return live_scan(request, context)
                else:
                    # Save scantype to db.
                    if request.user.is_authenticated():
                        user = request.user

                        str_scan_options = ''
                        for option in scan_options[:-1]:
                            str_scan_options += option + ','
                        str_scan_options += scan_options[-1]
                        print str_scan_options

                        new_scan = ScanType(scan_name=scan_name, user=user,
                                            host_address=host_address, ports=ports,
                                            scan_options=scan_options)
                        new_scan.save()

                # We're not exporting, so render the page with a table.
                return render(request, 'scans/scans.html', context)
            else:

                scan_name = request.POST.get("scan_name")
                host_address = request.POST.get("host_address")
                ports = request.POST.get("ports")

                scan_options = []

                dirty_scan_options = request.POST.get("scan_options")

                scan_obj = ScanType(scan_name=scan_name, user=request.user,
                                    host_address=host_address, ports=ports,
                                    scan_options=scan_options)

                if dirty_scan_options:
                    if 'version_detection' in dirty_scan_options:
                        scan_options.append('version_detection')
                    if 'os_and_services' in dirty_scan_options:
                        scan_options.append('os_and_services')
                    if 'fast' in dirty_scan_options:
                        scan_options.append('fast')
                    if 'no_ping' in dirty_scan_options:
                        scan_options.append('no_ping')

                # Append important info to context.

                context.update(csrf(request))
                context['scan_name'] = scan_name
                context['host_address'] = host_address
                context['ports'] = ports
                context['scan_options'] = scan_options

                if request.user.is_authenticated():
                    saved_scans = ScanType.objects.filter(user=request.user)
                    context['saved_scans'] = saved_scans

                scan_obj.scan_options = scan_options

                context.update(csrf(request))
                form = ScansForm(instance=scan_obj)
                context['form'] = form
                live_scanning = 'live_scan' in request.POST
                if live_scanning:
                    # Perform live nmap scan.
                    return live_scan(request, context)
                else:
                    # Save scantype to db.
                    if request.user.is_authenticated():
                        user = request.user

                        str_scan_options = ''
                        for option in scan_options[:-1]:
                            str_scan_options += option + ','
                        str_scan_options += scan_options[-1]
                        print str_scan_options

                        existing_scan_instance = None
                        if ScanType.objects.filter(scan_name=scan_name).exists():
                            existing_scan_instance = get_object_or_404(ScanType, scan_name=scan_name)

                        if not existing_scan_instance:
                            new_scan = ScanType(scan_name=scan_name, user=user,
                                                host_address=host_address, ports=ports,
                                                scan_options=scan_options)
                            new_scan.save()
                        else:
                            context['msg'] = 'Scan Name already exists. Delete the old one first.'

    context.update(csrf(request))
    context['form'] = ScansForm()
    return render(request, 'scans/scans.html', context)
