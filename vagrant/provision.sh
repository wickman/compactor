apt-get update
apt-get -y install \
    autoconf \
    git \
    libapr1 \
    libapr1-dev \
    libaprutil1 \
    libaprutil1-dev \
    libcurl4-openssl-dev \
    libsasl2-dev \
    libsvn-dev \
    libtool \
    maven \
    openjdk-7-jdk \
    python-dev \
    python-pip \
    zookeeper

# Ensure java 7 is the default java.
update-alternatives --set java /usr/lib/jvm/java-7-openjdk-amd64/jre/bin/java

# Set the hostname to the IP address.  This simplifies things for components
# that want to advertise the hostname to the user, or other components.
hostname 192.168.33.2

MESOS_VERSION=0.20.1

function build_mesos {
  # wget -q -c http://downloads.mesosphere.io/master/ubuntu/12.04/mesos_${MESOS_VERSION}-1.0.ubuntu1204_amd64.deb
  # dpkg --install mesos_${MESOS_VERSION}-1.0.ubuntu1204_amd64.deb
  
  git clone https://github.com/wickman/mesos mesos-fork
  pushd mesos-fork
    git checkout wickman/pong_example
    ./bootstrap
  popd
  mkdir -p mesos-build
  pushd mesos-build
    ../mesos-fork/configure
    pushd 3rdparty
      make
    popd
    pushd src
      make pong-process
    popd
  popd
  ln -s mesos-build/src/pong-process pong
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

install_ssh_config
install_tox
build_mesos
