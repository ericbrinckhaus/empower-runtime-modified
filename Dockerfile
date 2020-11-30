## build : docker build --build-arg CACHE_DATE="$(date)" -t empower-runtime2 .
## run :   docker run --net=host --rm --privileged -it empower-runtime2
## after run : apt install -y mongodb-org
## after run : /bin/sh entry.sh 

FROM ubuntu:20.04
MAINTAINER El Eric y El Eche  <ebrinckhaus@blueboot.com agustin.echeverria@basf.com>

# Installing python dependencies
RUN apt update
RUN apt -y install python3-pip wget unzip
RUN rm -rf /var/lib/apt/lists/*
RUN pip3 install tornado==6.0.4 construct==2.10.56 pymodm==0.4.3 influxdb==5.3.0 python-stdnum==1.13
RUN pip3 install requests==2.23.0
RUN pip3 install empower-core==1.0.5

# Install vim
RUN apt-get update
RUN apt-get -y install vim

# Install mongodb
RUN apt-get install -y gnupg
RUN apt-get install -y systemctl
RUN wget -qO - https://www.mongodb.org/static/pgp/server-4.4.asc | apt-key add -
RUN echo "deb [ arch=amd64,arm64 ] https://repo.mongodb.org/apt/ubuntu focal/mongodb-org/4.4 multiverse" | tee /etc/apt/sources.list.d/mongodb-org-4.4.list
RUN apt update
#RUN apt install -y mongodb-org
RUN mkdir -p /data/db

# Install influxdb
RUN apt -y install curl
RUN curl -sL https://repos.influxdata.com/influxdb.key | apt-key add -
RUN . /etc/lsb-release
RUN echo "deb https://repos.influxdata.com/${DISTRIB_ID,,} ${DISTRIB_CODENAME} stable" | tee /etc/apt/sources.list.d/influxdb.list
RUN apt-get -y install influxdb

ARG CACHE_DATE=2020-10-10
# Fetching the latest repository from empower-runtime
RUN wget https://github.com/ericbrinckhaus/empower-runtime-modified/archive/main.zip
RUN unzip main.zip
RUN rm main.zip
RUN ln -sf /empower-runtime-modified-main/conf/ /etc/empower
RUN mkdir -p /var/www/
RUN ln -s /empower-runtime-modified-main/webui/ /var/www/empower

# Create start up script entrypoint
RUN echo "cd empower-runtime-modified-main\nsystemctl enable mongod.service\nsystemctl start mongod.service\nservice influxdb start\npython3 script_db.py\npython3 empower-runtime.py" > entry.sh

# Run the controller
#ENTRYPOINT ["/bin/sh", "entry.sh"]

# Expose Web GUI
EXPOSE 8888

# Expose LVAPP Server
EXPOSE 4433

# Expose VBSP Server
EXPOSE 5533
