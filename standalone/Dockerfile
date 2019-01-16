FROM ubuntu:18.04
RUN apt update && \
    apt install -y libhyperscan-dev python3-pip
COPY requirements.txt /
RUN pip3 install -r /requirements.txt
ADD . /
ENTRYPOINT ["python3", "http_fetcher.py"]