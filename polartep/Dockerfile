FROM pytorch/pytorch

#Setup
ENV DEBIAN_FRONTEND=noninteractive
RUN sed 's/main$/main universe multiverse/' -i /etc/apt/sources.list
RUN apt-get update && apt-get install -y   build-essential   unzip   software-properties-common git

#Clone repo
RUN git clone https://github.com/NorskRegnesentral/ai4artic_snow.git ~/ai4artic_snow

# Setup code and requirements
RUN add-apt-repository ppa:ubuntugis/ppa
RUN apt-get update
RUN apt-get install -y gdal-bin
RUN ogrinfo --version
RUN apt-get install -y libgdal-dev
RUN export CPLUS_INCLUDE_PATH=/usr/include/gdal
RUN export C_INCLUDE_PATH=/usr/include/gdal
RUN pip install gdal==2.4.2
RUN pip install -r ~/ai4artic_snow/REQUIREMENTS.txt

# Add special entrypoint
ADD entrypoint.sh /tmp/entrypoint.sh
RUN chmod +x /tmp/entrypoint.sh

# Create workdir
WORKDIR /root/ai4artic_snow

COPY scihub_credentials.txt .
COPY creodias_credentials.txt .

# Set entrypoint
ENTRYPOINT ["/tmp/entrypoint.sh"]


