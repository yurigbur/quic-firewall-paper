QUIC Testing Setup

*Tested with Ubuntu 20.04 64bit and Ubuntu Server 20.04 64bit
Kernel: Linux ubuntu 5.4.0-52-generic
All tools used are build on the IETF quic and http3 draft version 29: https://tools.ietf.org/html/draft-ietf-quic-http-29 and https://tools.ietf.org/html/draft-ietf-quic-transport-29*
**This setup describes localhost usage of client and server. The same steps should be applicable for two different systems. Change localhost to the right IP addresses where necessary**

## Prerequisites
* Install required build and anaylsis tools (everything else should be present on ubuntu)
	```
	sudo apt install cargo cmake build-essential autoconf libtool libpcre3 libpcre3-dev zlib1g zlib1g-dev pkg-config conntrack wireshark
	```
* Install quiche
*Tested with  commit 26871b7c9ac10dd9f9e55bf216586935b9c39cf8*
	```
	git clone --recursive https://github.com/cloudflare/quiche
	cd quiche
	cargo build --release --features pkg-config-meta,qlog
	mkdir deps/boringssl/src/lib
 	ln -vnf $(find target/release -name libcrypto.a -o -name libssl.a) deps/boringssl/src/lib/
	cd ..
	```
### Curl client with quiche
*Tested with commit b2bde86bbb18ba33c024837485335ede2a9b789a*
* Install curl
	```
	git clone https://github.com/curl/curl
	cd curl
	./buildconf
	./configure LDFLAGS="-Wl,-rpath,$PWD/../quiche/target/release" --with-ssl=$PWD/../quiche/deps/boringssl/src --with-quiche=$PWD/../quiche/target/release
	make
	```
	**Test Curl**
	I had issues that the openssl version does not support http3. If this is the case, re-link the boringssl lib again in the quiche directory and than build curl again.
	```
	./src/curl --http3 https://quic.tech:8443/
	cd ..
	```
### Patch nginx server with quiche
* Download nginx source
	```
	curl -O https://nginx.org/download/nginx-1.16.1.tar.gz
	tar xzvf nginx-1.16.1.tar.gz
	```
* Patch nginx source
	```
	cd nginx-1.16.1
	patch -p01 < ../quiche/extras/nginx/nginx-1.16.patch
	```
* build nginx
	```
	./configure \
       --prefix=/etc/nginx \
	   --sbin-path=/usr/sbin/nginx \
	   --modules-path=/usr/lib/nginx/modules \
       --conf-path=/etc/nginx/nginx.conf \
       --error-log-path=/var/log/nginx/error.log \
       --pid-path=/var/run/nginx.pid \
       --lock-path=/var/run/nginx.lock \
       --user=nginx \
       --group=nginx \
       --build="quiche-$(git --git-dir=../quiche/.git rev-parse --short HEAD)" \
       --with-http_ssl_module \
       --with-http_v2_module \
       --with-http_v3_module \
       --with-openssl=../quiche/deps/boringssl \
       --with-quiche=../quiche \
	   --http-log-path=/var/log/nginx/access.log
	make
	```
* Install nginx
	```
	sudo make install
	cd ..
	sudo ln -s /usr/lib/nginx/modules /etc/nginx/modules
	```
	**Test nginx**
	Test version. Should show something like: `nginx version: nginx/1.16.1 (quiche-fd5e028)`
	```
	sudo nginx -V
	```
	Test configuration. Should state that syntax is ok and test is successful.
	```
	sudo nginx -t
	```
* Setup nginx service
	Create nginx user
	```
	sudo adduser --system --home /nonexistent --shell /bin/false --no-create-home --disabled-login --disabled-password --gecos "nginx user" --group nginx
	```
	Create the `nginx.service` file
	```
	sudo vim /etc/systemd/system/nginx.service 
	```
	and enter the following content:
	```
	[Unit]
	Description=nginx - high performance web server
	Documentation=https://nginx.org/en/docs/
	After=network-online.target remote-fs.target nss-lookup.target
	Wants=network-online.target

	[Service]
	Type=forking
	PIDFile=/var/run/nginx.pid
	ExecStartPre=/usr/sbin/nginx -t -c /etc/nginx/nginx.conf
	ExecStart=/usr/sbin/nginx -c /etc/nginx/nginx.conf
	ExecReload=/bin/kill -s HUP $MAINPID
	ExecStop=/bin/kill -s TERM $MAINPID

	[Install]
	WantedBy=multi-user.target
	```
	Enable and start the service
	```
	sudo systemctl enable nginx.service
	sudo systemctl start nginx.service
	```
* Configure nginx server
	Create self-singed certificate:
	```
	sudo openssl req -x509 -nodes -days 365 -newkey rsa:2048 -keyout /etc/ssl/private/nginx_cert.key -out /etc/ssl/certs/nginx_cert.crt
	```
	Create a `.pem` filte for self-signed certificate to pass to curl for certificate verification
	```
	sudo openssl x509 -in /etc/ssl/certs/nginx_cert.crt -outform PEM > curl/src/nginx_cert.pem
	```
	
	Open the `nginx.conf`
	```
	sudo vim /etc/nginx/nginx.conf
	```
	and add the following lines inside the `server` configuration (remove default lines for listening port and adjust `server_name` if necessary):
	```
	listen 443 quic reuseport;
	listen 443 ssl http2;
    server_name  localhost;

	ssl_certificate		/etc/ssl/certs/nginx_cert.crt;
	ssl_certificate_key	/etc/ssl/private/nginx_cert.key;

	ssl_protocols TLSv1.2 TLSv1.3;

	proxy_request_buffering off;

	add_header alt-svc 'h3-29=":443"; ma=86400';

	```
	Restart nginx
	```
	sudo systemctl restart nginx
	```
	
## Test the Setup
Monitor the traffic with e.g. wireshark
* Test "normal" http:
	```
	./curl/src/curl --cacert curl/src/nginx_cert.pem https://127.0.0.1
	```
* Test http/3
	```
	./curl/src/curl --http3 --cacert curl/src/nginx_cert.pem https://127.0.0.1
	```
In both cases, the nginx default page should be returned but the capture should show TCP/TLS in the first case and QUIC in the second case.

![06e1a833c0e48b947714f407c72bf6e8.png](../_resources/aefcba205d324cddb5f977bce8c94bf3.png)


## Setup Firewall
**TODO**