import urllib2
import socket

try:
    ip = '173.194.127.180'
    request = urllib2.Request('http://%s' % ip, headers={'Host': 'ul2test001.appspot.com'})
    #request = urllib2.Request('http://%s' % ip, headers={'Host': '173.194.127.180'})
    response = urllib2.urlopen(request)
    #response = urllib2.urlopen('https://www.google.com')
    #response = urllib2.urlopen('http://173.194.127.180/')

    print response

    the_page = response.read()    
    print the_page  
except socket.error as e:
    print e



