

from gevent import pool  
g = pool.Pool()  
def a():  
    for i in xrange(100):  
        g.spawn(b)  
def b():  
    print 'b'  
g.spawn(a)  
g.join()  