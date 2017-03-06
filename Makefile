PACKAGE := /tmp/unfollow-notifications.zip
VENV_DIR := ~/.virtualenvs/unfollow-notifications
SITE_PKG_DIR := $(VENV_DIR)/lib/python2.7/site-packages
SRC_FILES := find . -type f -name "*.py"

$(PACKAGE): venv test
	( cd $(SITE_PKG_DIR) ; zip -rv $@ . )
	$(SRC_FILES) | xargs zip -rv $@

.PHONY: test
test:
	$(SRC_FILES) | xargs flake8

venv: $(VENV_DIR)/bin/activate

$(VENV_DIR)/bin/activate: requirements.txt
	rm -rf $(VENV_DIR)
	mkdir -p $(VENV_DIR)
	( cd $(VENV_DIR)/.. ; virtualenv -p `which python2.7` unfollow-notifications )
	$(VENV_DIR)/bin/pip install -r requirements.txt

