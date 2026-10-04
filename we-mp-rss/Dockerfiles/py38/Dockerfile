FROM ghcr.io/rachelos/rachel_base_os:latest


WORKDIR /app
RUN ls
COPY  requirements.txt .
RUN pip3 install -r requirements.txt -i https://pypi.tuna.tsinghua.edu.cn/simple

