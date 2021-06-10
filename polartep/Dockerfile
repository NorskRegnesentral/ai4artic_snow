FROM pytorch/pytorch

#Setup
ENV DEBIAN_FRONTEND=noninteractive
RUN sed 's/main$/main universe multiverse/' -i /etc/apt/sources.list
RUN apt-get update && apt-get install -y   build-essential   unzip   software-properties-common git
RUN apt -y update && apt -y install \
        make \
        build-essential \
        libssl-dev \
        zlib1g-dev \
        libbz2-dev \
        libreadline-dev \
        libsqlite3-dev \
        wget \
        curl \
        llvm \
        libncurses5-dev \
        xz-utils \
        tk-dev \
        libxml2-dev \
        libxmlsec1-dev \
        libffi-dev \
        liblzma-dev

#Clone repo
RUN git clone https://github.com/NorskRegnesentral/ai4artic_snow.git ~/ai4artic_snow

# Setup code and requirements
RUN pip install -r ~/ai4artic_snow/REQUIREMENTS.txt

# Add special entrypoint
ADD entrypoint.sh /tmp/entrypoint.sh
RUN chmod +x /tmp/entrypoint.sh

# Create workdir
WORKDIR ~/ai4artic_snow

COPY scihub_credentials.txt .
COPY creodias_credentials.txt .

# Set entrypoint
ENTRYPOINT ["/tmp/entrypoint.sh"]


