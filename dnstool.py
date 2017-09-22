#!/usr/bin/python
# -*- coding: utf-8 -*-

# pip install gevent
# pip install dnspython

import gevent, gevent.monkey; gevent.monkey.patch_all()
import socket, urllib2, logging, time, random, os
import dns.name, dns.message, dns.query
import pprint

logging.basicConfig(level = logging.CRITICAL)

class DnsTool(object):
    def __init__(self):
        self.google_check_host = 'www.google.com.hk'
        self.google_hosts = ['www.google.com', 'mail.google.com', 'www.google.com.hk', 'www.google.com.tw', 'www.l.google.com']
        #dnsservers = ['114.114.114.114', '114.114.115.115', '8.8.8.8', '8.8.4.4']
        self.google_iplist_file = 'google_iplist.txt'
        self.dnsservers = self.load_iplist_from_file('foreign_dns.txt')
        self.logger = logging.getLogger('DnsTool')
        self.logger_level = {'debug': logging.DEBUG, 'info': logging.INFO, 'warning': logging.WARNING, 'error': logging.ERROR, 'critical': logging.CRITICAL}

    def set_log_level(self, level):
        self.logger.setLevel(self.logger_level[level])

    def get_host_iplist_from_resolve(self, check_host, hosts = [], init_iplist = [], min_ip_cnt = 50):
        if not hosts: hosts = [check_host]
        if not isinstance(hosts, list): hosts = [hosts]
        iplist = init_iplist + self.resolve_iplist(hosts, self.dnsservers)
        iplist_info = self.profile_connect(check_host, iplist)
        self.logger.info('profile iplist(1) [num %d] host [%s]: %s', len(iplist_info), check_host, iplist_info)
        if len(iplist_info) < min_ip_cnt:
            test_expand_list = self.expand_iplist(iplist, element_num = 100)
            for iplist in test_expand_list:
                iplist_info += self.profile_connect(check_host, iplist)
                self.logger.info('profile iplist(1) [num %d] host [%s]: %s', len(iplist_info), check_host, iplist_info)
                if len(iplist_info) >= min_ip_cnt: break
        iplist_info.sort(key = lambda x: x[1])
        return iplist_info

    def get_host_iplist_from_file(self, check_host, iplist_file, min_ip_cnt = 30, max_ip_search = 5000):
        ip_list = self.load_iplist_from_file(iplist_file)
        random.shuffle(ip_list)
        self.logger.info('iplist file have %d ip candidates for host [%s].', len(ip_list), check_host)
        iplist_info = []
        total_test_num = 0
        while ip_list and len(iplist_info) < min_ip_cnt and total_test_num < max_ip_search:
            test_num = min(len(ip_list), 100)
            total_test_num += test_num
            iplist, ip_list = ip_list[:test_num], ip_list[test_num:]
            iplist_info += self.profile_connect(check_host, iplist)
            self.logger.info('profile iplist(1) [num %d] host [%s]: %s', len(iplist_info), check_host, iplist_info)
        iplist_info.sort(key = lambda x: x[1])
        return iplist_info

    def resolve_iplist(self, hosts, dnsservers = []):
        def do_remote_resolve(host, dnsserver, resolved_iplist):
            iplist = self.remote_resolve(host, dnsserver)
            if iplist:
                resolved_iplist += iplist
                self.logger.info('remote resolve host[%s] from dnsserver[%s]: iplist=%s', host, dnsserver, iplist)
        def do_local_resolve(host, resolved_iplist):
            try:
                iplist = socket.gethostbyname_ex(host)[-1]
                resolved_iplist += iplist
                self.logger.info('local resolve host[%s]: iplist=%s', host, iplist)
            except (socket.error, OSError):
                pass
        if not isinstance(hosts, list): hosts = [hosts]
        if not isinstance(dnsservers, list): dnsservers = [dnsservers]
        resolved_iplist = []
        gevent.joinall([gevent.spawn(do_local_resolve, host, resolved_iplist) for host in hosts] +
                       [gevent.spawn(do_remote_resolve, host, dnsserver, resolved_iplist) for dnsserver in dnsservers for host in hosts])
        return list(set(resolved_iplist))

    def remote_resolve(self, host, dnsserver, timeout = 2, udp = False):
        try:
            request = dns.message.make_query(dns.name.from_text(host), dns.rdatatype.A)
            query = dns.query.udp if udp else dns.query.tcp
            response = query(request, dnsserver, timeout = timeout)
            if response.answer:
                return sum(map(lambda ans: [addr.address for addr in ans], [ans for ans in response.answer if ans.rdtype == dns.rdatatype.A]), [])
            else:
                return []
        except dns.exception.Timeout:
            return []
        except:  # remote connection failed
            return []

    def expand_iplist(self, iplist, element_num = 100):
        cranges = set(x.rpartition('.')[0] for x in iplist)
        iplist = list(set(['%s.%d' % (c, i) for c in cranges for i in xrange(1, 254)]) - set(iplist))
        random.shuffle(iplist)
        expand_iplist = []
        while len(iplist) > element_num:
            iplist1, iplist = iplist[:element_num], iplist[element_num:]
            expand_iplist.append(iplist1)
        expand_iplist.append(iplist1)
        return expand_iplist

    def ip_to_num(self, ip):
        return reduce(lambda x,(y,z): x+int(y)*z, zip(ip.split('.'), [256**3, 256**2, 256, 1]), 0)

    def num_to_ip(self, num):
        return '.'.join([str(x) for x in [num/256**3, num%256**3/256**2, num%256**2/256, num%256]])

    def iplist_from_range(self, ip_range):
        if not '/' in ip_range: raise Exception('invalid ip range format %s' % ip_range)
        ip_addr_base, ip_mask_num = ip_range.split('/')
        ip_range_num = 2**(32 - int(ip_mask_num))
        ip_base_addr_num = self.ip_to_num(ip_addr_base)
        if ip_base_addr_num % ip_range_num: raise Exception('invalid ip range format %s' % ip_range)
        return [self.num_to_ip(ip_base_addr_num + i) for i in xrange(1, ip_range_num) if (ip_base_addr_num + i)%256 not in [0, 255]]

    def connect_ip(self, host, ip):
        try:
            request = urllib2.Request('https://%s' % ip, headers={'Host': host})
            response = urllib2.urlopen(request, timeout = 3)
            page = response.read()
            return page
        #except (socket.error, urllib2.URLError) as e:
        except Exception as e:
            self.logger.error('fetch host[%s] ip[%s] fail: %s', host, ip, e)
            return []

    def ping_ip(self, ip, count = 2, wait = 1):
        success = not os.system('ping -n %d -w %d %s > NUL' % (count, wait, ip))
        return success

    def profile_connect(self, host, iplist):
        def do_fetch(host, ip, result_list):
            start = time.time()
            page = self.connect_ip(host, ip)
            if page:
                consume =  time.time()-start
                result_list.append((ip, consume))
                self.logger.debug('fetch host[%s] ip[%s], consume time %ss.', host, ip, consume)
        result_list = []
        gevent.joinall([gevent.spawn(do_fetch, host, ip, result_list) for ip in set(iplist)])
        return result_list

    def profile_ping(self, iplist):
        def do_ping(ip, result_list):
            start = time.time()
            success = self.ping_ip(ip)
            consume =  time.time()-start
            if success:
                result_list.append((ip, consume))
                self.logger.debug('ping ip[%s], consume time %ss.', ip, consume)
            else:
                self.logger.debug('ping ip[%s] fail, consume time %ss.', ip, consume)
        result_list = []
        gevent.joinall([gevent.spawn(do_ping, ip, result_list) for ip in set(iplist)])
        return result_list

    def gen_google_iplist_file(self, ip_range_file, iplist_file):
        with open(ip_range_file, 'r') as f:
            iplist = []
            for line in f:
                try:
                    iplist += self.iplist_from_range(line.strip().split()[0])
                except Exception as e:
                    pass #print e
        with open(iplist_file, 'w') as f_write:
            for ip in set(iplist):
                f_write.write('%s\n' % ip)

    def load_iplist_from_file(self, file):
        with open(file, 'r') as f:
            iplist = []
            for line in f:
                try:
                    num = self.ip_to_num(line.strip())
                    iplist.append(line.strip())
                except: pass
        return iplist


if __name__ == '__main__':
    choose = 5
    dnstool = DnsTool()
    dnstool.set_log_level('info')
    if choose == 1:
        #host = 'encrypted.google.com'
        host = 'www.youtube.com'
        dnsserver = '8.8.8.8'
        iplist = dnstool.remote_resolve(host, dnsserver, timeout = 2, udp = True)
        print iplist
        iplist = dnstool.remote_resolve(host, dnsserver, timeout = 2, udp = False)
        print iplist
    elif choose == 2:
        ip_list = ['173.194.72.100', '173.194.72.101', '173.194.72.138', '173.194.72.113', '173.194.72.139', '173.194.72.102']
        #host = 'ul2test001.appspot.com'
        host = 'www.youtube.com'
        info = dnstool.profile_connect(host, ip_list)
        pprint.pprint(info)
    elif choose == 3:
        dnstool.gen_google_iplist_file('google_ip_range.txt', 'google_iplist.txt')
    elif choose < 10:
        start = time.time()
        if choose == 4:
            iplist_info = dnstool.get_host_iplist_from_file(dnstool.google_check_host, dnstool.google_iplist_file)
        elif choose == 5:
            iplist_info = dnstool.get_host_iplist_from_resolve(dnstool.google_check_host, hosts = dnstool.google_hosts)
        elif choose == 6:
            ip1 = '121.78.74.99|123.205.251.80|202.39.143.20|202.39.143.84|203.211.0.20|218.189.25.167|202.39.143.84|202.39.143.88|202.39.143.89|203.66.124.251|60.199.175.95|61.219.131.88|61.219.131.89|61.219.131.93|61.219.131.94|61.219.131.98|61.219.131.99|60.199.175.89|218.176.242.178|203.66.124.251|203.66.124.246|203.66.124.226|202.39.143.98|202.39.143.30|103.25.178.27|203.66.124.216|202.39.143.119|203.66.124.227|202.39.143.113|202.39.143.114|103.25.178.30|103.25.178.38|203.66.124.182|203.66.124.232|202.39.143.108|60.199.175.25|1.179.248.158|203.66.124.183|203.66.124.212|103.25.178.42|103.25.178.19|202.39.143.20|61.219.131.104|202.39.143.84'
            ip2 = '123.205.250.132|123.205.250.80|123.205.251.112|123.205.251.80|163.28.116.18|163.28.83.146|202.39.143.20|202.39.143.84|203.211.0.20'
            ip_list = ip1.split('|') + ip2.split('|')
            iplist_info = dnstool.get_host_iplist_from_resolve(hosts = dnstool.google_hosts, init_iplist = ip_list)
        consume =  time.time()-start
        time.sleep(2)
        print 'consume ', consume
        print 'search result: number of ip ', len(iplist_info)
        pprint.pprint(iplist_info)
        ip_string = '|'.join([ip for ip, time in iplist_info])
        print ip_string

    if False:
        filepath = '/Users/carol/Software/goagent-goagent-5558ae2/local'
        filename = os.path.join(filepath, 'proxy.ini')
        lines = open(filename, 'r').readlines()
        change_lines = []
        for line in lines:
            line = line.rstrip()
            if line.startswith('google_cn ='):
                change_lines.append('google_cn = %s' % ip_string)
            elif line.startswith('google_hk ='):
                change_lines.append('google_hk = %s' % ip_string)
            else:
                change_lines.append(line)
        with open(filename, 'w') as f_write:
            for line in change_lines:
                f_write.write(line + '\n')
        os.system(r'python %s' % os.path.join(filepath, 'proxy.py'))




