.PHONY: notebook ## run notebook from host or inside container
notebook:
	@TOKEN="$(JUPYTER_TOKEN)"; \
	echo "Jupyter token: $$TOKEN"; \
	echo "Copy this into the browser password prompt."; \
	if command -v docker >/dev/null 2>&1; then \
		docker exec $(PROJECT_NAME)-pythonenv /bin/sh -c "uv run --extra dev jupyter notebook --port=8000 --ip=0.0.0.0 --NotebookApp.token=$$TOKEN"; \
	else \
		uv run --extra dev jupyter notebook --port=8000 --ip=0.0.0.0 --NotebookApp.token=$$TOKEN; \
	fi