apt-get update
apt-get -y install \
    openjdk-7-jdk \
    python-pip \
    zookeeper
        

# Ensure java 7 is the default java.
update-alternatives --set java /usr/lib/jvm/java-7-openjdk-amd64/jre/bin/java

# Set the hostname to the IP address.  This simplifies things for components
# that want to advertise the hostname to the user, or other components.
hostname 192.168.33.2

MESOS_VERSION=0.20.1

function install_mesos {
  wget -q -c http://downloads.mesosphere.io/master/ubuntu/12.04/mesos_${MESOS_VERSION}-1.0.ubuntu1204_amd64.deb
  dpkg --install mesos_${MESOS_VERSION}-1.0.ubuntu1204_amd64.deb
}

function install_ssh_config {
  cat >> /etc/ssh/ssh_config <<EOF

# Allow local ssh w/out strict host checking
Host $(hostname)
    StrictHostKeyChecking no
    UserKnownHostsFile /dev/null
EOF
}

function install_tox {
  pip install tox
}

function prepare_zookeeper {
  cp /vagrant/vagrant/configs/zookeeper.conf /etc/init
}

function start_services {
  start zookeeper
  start mesos-master
  start mesos-slave GLOG_v=5
}

install_mesos
install_ssh_config
install_tox
prepare_zookeeper
start_services
