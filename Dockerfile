FROM python:3.8-slim

ADD requirements.txt /requirements.txt
RUN pip install -r /requirements.txt
ADD main.py /main.py

ENTRYPOINT ["python", "/main.py"]
