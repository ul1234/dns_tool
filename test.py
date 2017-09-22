import dns.name
import dns.message
import dns.query
import dns.flags

################
import socket
import os

method0 = 1 # False
method1 = 1 #True

#qname = 'www.google.com.hk11'
qname = 'google.com.hk'
#name_server = '8.8.8.8'
dnsserver = '114.114.114.114'
    
if method0:
    data = os.urandom(2)
    data += b'\x01\x00\x00\x01\x00\x00\x00\x00\x00\x00'
    data += ''.join(chr(len(x))+x for x in qname.split('.')).encode()
    data += b'\x00\x00\x01\x00\x01'
                
    sock = socket.socket(family=socket.AF_INET, type=socket.SOCK_DGRAM)
    sock.settimeout(2)
    sock.sendto(data, (dnsserver, 53))
    
    data = sock.recv(512)
    print data
    #if data and not DNSUtil.is_bad_reply(data):
    #    return data[2:]

if method1:
    request = dns.message.make_query(dns.name.from_text(qname), dns.rdatatype.A)
    response = dns.query.udp(request, dnsserver, timeout = 2)
    print response.answer
    if response.answer:
        for i in xrange(len(response.answer[0])):
            print response.answer[0][i]
    if False:
        domain = dns.name.from_text(qname)
        print 'domain:' + str(domain)
        if not domain.is_absolute():
            domain = domain.concatenate(dns.name.root)
            print 'abs domain:' + str(domain)

        request = dns.message.make_query(qname, dns.rdatatype.A)
        #request.flags |= dns.flags.RD
        #request.find_rrset(request.additional, dns.name.root, ADDITIONAL_RDCLASS,
        #                   dns.rdatatype.OPT, create=True, force_unique=True)
        print 'request:' + str(request)

        response = dns.query.udp(request, dnsserver)
        #response = dns.query.tcp(request, name_server)


        print '#####################'
        #print response
        for i in xrange(len(response.answer[0])):
            print response.answer[0][i]
        #print response.additional
        #print response.authority






    
    
