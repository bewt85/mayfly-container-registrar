# Docker version 1.0.0

FROM bewt85/etcdctl:0.4.1 

RUN apt-get update
RUN apt-get install -y python2.7 python-dev libssl-dev vim git wget
RUN wget https://bootstrap.pypa.io/get-pip.py -O /tmp/get-pip.py && python /tmp/get-pip.py

ADD requirements.txt     /etc/mayfly/
RUN pip install -r       /etc/mayfly/requirements.txt

ADD bin                  /usr/local/bin/

CMD '/usr/local/bin/updateContainersForever.sh'
