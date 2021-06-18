VERSION=$(shell cat VERSION | head -1)
INCLUDED_FILES = Dockerfile README.md  grafana_alerts_exporter.py grafana_alerts_exporter.yml requirements.txt
PROJECT = grafana_alerts_exporter

release: tag
	@echo "releasing v$(VERSION)..."
	@tar -zcf $(PROJECT)-$(VERSION).tar.gz $(INCLUDED_FILES)
	@echo "Created file $(PROJECT)-$(VERSION).tar.gz"
	@zip -rq $(PROJECT)-$(VERSION).zip $(INCLUDED_FILES)
	@echo "Created file $(PROJECT)-$(VERSION).zip"
	@echo "Release ready: v$(VERSION)"

tag: commit
	@git tag v$(VERSION)
	@git push --tags
	@echo "Created tag v$(VERSION)"

commit:
	
	@git add .
	@git commit -m"Committed v$(VERSION)"
	@git push
	@echo "Committed and pushed to current branch."


clean: 
	@rm -vf grafana_alerts_exporter-*.tar.gz
	@rm -vf grafana_alerts_exporter-*.zip
	@echo "Cleaned project"

.PHONY: release clean tag commit