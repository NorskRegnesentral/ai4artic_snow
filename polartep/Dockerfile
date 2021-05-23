FROM pytorch/pytorch

#Setup
RUN sed 's/main$/main universe multiverse/' -i /etc/apt/sources.list
RUN apt-get update && apt-get install -y   build-essential   unzip   software-properties-common

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

# Set entrypoint
ENTRYPOINT ["/tmp/entrypoint.sh"]


