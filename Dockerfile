FROM nvidia/cuda:10.1-base-ubuntu18.04

RUN apt-get update && apt-get install -y --no-install-recommends software-properties-common &&  apt-add-repository multiverse
RUN echo "ttf-mscorefonts-installer msttcorefonts/accepted-mscorefonts-eula select true" | debconf-set-selections

RUN apt-get update -q &&  apt-get install -q -y \
        bash \
	bzip2 \
        ca-certificates \
        git \
        libglib2.0-0 \
        libsm6 \
        libxext6 \
        libxrender1 \
        mercurial \
        subversion \
        wget \
	vim \
	parallel \
	xvfb \
	wkhtmltopdf \
        docker \
        docker.io \
	fontconfig \
	jq \
	imagemagick \
	coreutils \
	openjdk-8-jdk \
	parallel \
	ttf-mscorefonts-installer \
	fontconfig && fc-cache -f -v

ENV PATH /opt/conda/bin:$PATH

RUN wget --quiet https://repo.anaconda.com/miniconda/Miniconda3-latest-Linux-x86_64.sh -O miniconda.sh && \
        mkdir -p /opt && \
        bash miniconda.sh -b -p /opt/conda && \
        rm miniconda.sh  && \
        ln -s /opt/conda/etc/profile.d/conda.sh /etc/profile.d/conda.sh && \
        echo ". /opt/conda/etc/profile.d/conda.sh" >> ~/.bashrc && \
        echo "conda activate base" >> ~/.bashrc

#FROM frolvlad/alpine-miniconda3
#RUN apk update && apk upgrade && \
#    apk add --no-cache bash git openjdk8-jre parallel xvfb xvfb-run wkhtmltopdf

#RUN apk --no-cache add msttcorefonts-installer fontconfig && \
#    update-ms-fonts && \
#    fc-cache -f

#RUN apk add jq imagemagick

RUN cp /usr/bin/Xvfb /usr/bin/xvfb
RUN mkdir ~/.parallel
RUN touch ~/.parallel/will-cite

RUN mkdir /NIST-data /outputs /app
RUN chmod -R 777 /NIST-data /outputs /app

# INSTALL SCRIPTS SUMMARIZATION PIPELINE CODE AND DEPENDENCIES 
WORKDIR /app
RUN conda install pytorch torchvision torchaudio cpuonly -c pytorch
ADD scripts /app/scripts
RUN cd /app/scripts; python setup.py develop

ADD CLIR-Summarization-19 CLIR-Summarization-19
RUN cd /app/CLIR-Summarization-19; python setup.py develop
RUN pip install -U sacremoses sentencepiece websocket-client

ENV SCRIPTS=/app/scripts
ENV PATH=${SCRIPTS}/docker/bin:${PATH}
RUN python -m nltk.downloader -d /usr/local/share/nltk_data stopwords
RUN python -m nltk.downloader -d /usr/local/share/nltk_data punkt

ADD models /models
ADD tools /tools
ENV PYTHONUNBUFFERED=True
ENV PYTHONWARNINGS=ignore::DeprecationWarning:nltk

# PORT NUMBER SETUP
ENV QUERYREL_PORT=8501
ENV PSQ_PORT=8502

ENV MORPH_PORT=8600
ENV DOC_PORT=8601
ENV QUERY_PORT=8602
ENV ANNOTATION_PORT=8603
ENV TRANSLATION_PORT=9000

RUN mkdir -p /query
RUN chmod -R 777 /NIST-data /outputs /app /query

ENTRYPOINT ["server_full"]
