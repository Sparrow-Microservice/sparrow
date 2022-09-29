
local-service:
	FLASK_ENV=dev NEED_REGISTER=True python {{cookiecutter.project_name_snake}}/server.py

container-up:
	dev {{cookiecutter.project_name_hyphen}} up

container-service:
	dev {{cookiecutter.project_name_hyphen}} sh FLASK_ENV=dev NEED_REGISTER=True python {{cookiecutter.project_name_snake}}/server.py

