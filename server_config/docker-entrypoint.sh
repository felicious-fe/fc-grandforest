#mkdir /tmp/featurecloud
#chmod 777 /tmp/featurecloud
#mount -t tmpfs -o size=512m ramdisk01 /tmp/featurecloud

/usr/bin/supervisord -c "/supervisord.conf"
