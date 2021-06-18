VERSION = $(shell cat VERSION | head -1)
INCLUDED_FILES = Dockerfile README.md  grafana_alerts_exporter.py grafana_alerts_exporter.yml requirements.txt
PROJECT = grafana_alerts_exporter

GIT_STATUS_COMMIT = $(shell test $$(git status | grep 'nothing to commit' | wc -l) = 1 && echo 0 || echo 1)
GIT_STATUS_PUSH = $(shell test $$(git status | grep 'Your branch is up to date' | wc -l) = 1 && echo 0 || echo 1)

test: 
	echo $(GIT_STATUS_COMMIT)
	echo $(GIT_STATUS_PUSH)

release: tag
	@echo "releasing v$(VERSION)..."
	@tar -zcf $(PROJECT)-$(VERSION).tar.gz $(INCLUDED_FILES)
	@echo "Created file $(PROJECT)-$(VERSION).tar.gz"
	@zip -rq $(PROJECT)-$(VERSION).zip $(INCLUDED_FILES)
	@echo "Created file $(PROJECT)-$(VERSION).zip"
	@echo "Release ready: v$(VERSION)"

commit:
ifeq ($(GIT_STATUS_COMMIT),1)
	@git add .
	@git commit -m"Committed v$(VERSION)"
endif

push: commit
ifeq ($(GIT_STATUS_PUSH),1)
	@git push
	@echo "Committed and pushed to current branch."
else ifeq ($(GIT_STATUS_COMMIT),1)
	@git push
	@echo "Committed and pushed to current branch."
endif

tag: push
	@git tag v$(VERSION)
	@git push --tags
	@echo "Created tag v$(VERSION)"


clean: 
	@rm -vf grafana_alerts_exporter-*.tar.gz
	@rm -vf grafana_alerts_exporter-*.zip
	@echo "Cleaned project"

.PHONY: release clean tag commit push