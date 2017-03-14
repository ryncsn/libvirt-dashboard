A webservice to manage auto test cases statics, powered by Flask.

For a faster start up, you need pipenv

Install Requirement For Flask:

    pipenv install

Install Requirement For Js:

    npm install

Build bundle files:

    ./node_modules/webpack/bin/webpack.js

Run Server:

    ./app.py runserver

Test Flask server:

    ./test.py

Generate some fixtures:

    ./test.py --fixture

Upgrade db from older version:

    ./app.py db upgrade

Integrate With apache-wsgi:

    Selinux config:

        setsebool -P httpd_can_network_connect 1
        chcon /path/to/dashboard/instance -t httpd_sys_content_t -R

    Create a .wsgi file (eg. /var/www/libvirt-dashboard/libvirt-dashboard.wsgi):

        import sys
        sys.path.insert(0, '/path/to/dashboard/instance/')

        from app import app as application

    Create virtual host file:

        <VirtualHost libvirt-dashboard.domain.com:80>
            WSGIDaemonProcess libvirt-dashboard user=nobody group=nobody threads=5 python-path=/var/www/libvirt-dashboard
            WSGIScriptAlias / /var/www/libvirt-dashboard/wsgi.py

            <Directory /var/www/libvirt-dashboard>
                WSGIProcessGroup libvirt-dashboard
                WSGIApplicationGroup %{GLOBAL}
                Require all granted
            </Directory>
        </VirtualHost>
