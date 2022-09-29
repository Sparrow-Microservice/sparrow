FROM harbor.infra.wish-cn.com/wish/{{cookiecutter.project_name_hyphen}}/api-base:latest

ARG proj_name={{cookiecutter.project_name}}
ARG proj_name_snake={{cookiecutter.project_name_snake}}

COPY . /production/$proj_name/current/$proj_name
RUN rm -rf /production/$proj_name/current/$proj_name/.git
WORKDIR /production/$proj_name/current/$proj_name

#Start from pip 20.3, a new resolver (2020-resolver) will be default.
#Add "--use-deprecated=legacy-resolver" to resolve package version conflict.
RUN /production/$proj_name/persistent/virtualenv/bin/pip --exists-action w install -r /production/$proj_name/current/$proj_name/$proj_name_snake/requirements/pip-requirements
RUN rm -rf /root/.cache

#i8n compile
RUN /production/$proj_name/persistent/virtualenv/bin/wish-flask i18n compile

CMD ["/bin/bash", "-c", "while true ; do sleep 3600; done"]

# start container using FLASK_ENV=dev /production/$proj_name/persistent/virtualenv/bin/python /production/$proj_name/current/$proj_name/$proj_name/server.py