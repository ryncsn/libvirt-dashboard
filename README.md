A webservice to manage auto test cases statics, powered by Flask.

Install Requirement:
pip install -r requirement.txt


Run Server:
./app.py runserver

Test:
./test.py

Upgrade db from older version:
./app.py db upgrade


With apache-wsgi:

Selinux config:
    setsebool -P httpd_can_network_connect 1
    chcon /path/to/dashboard/instance -t httpd_sys_content_t -R

Create a .wsgi file (eg. /var/www/libvirt-dashboard/libvirt-dashboard.wsgi):
    import sys
    sys.path.insert(0, '/path/to/dashboard/instance/')

    from app import app as application

Create virtual host file:
    <VirtualHost libvirt-dashboard.domain.com:80>
        WSGIDaemonProcess libvirt-dashboard user=nobody group=nobody threads=5
        WSGIScriptAlias / /var/www/libvirt-dashboard/libvirt-dashboard.wsgi

        <Directory /var/www/libvirt-dashboard>
            WSGIProcessGroup libvirt-dashboard
            WSGIApplicationGroup %{GLOBAL}
            Require all granted
        </Directory>
    </VirtualHost>
