VERSION=$(shell cat VERSION | head -1)
INCLUDED_FILES = Dockerfile README.md  grafana_alerts_exporter.py grafana_alerts_exporter.yml requirements.txt
PROJECT = grafana_alerts_exporter

release: tag
	echo "releasing v$(VERSION)"
	tar -zcvf $(PROJECT)-$(VERSION).tar.gz $(INCLUDED_FILES)
	zip -r $(PROJECT)-$(VERSION).zip $(INCLUDED_FILES)

clean: 
	rm -f grafana_alerts_exporter-*.tar.gz
	rm -f grafana_alerts_exporter-*.zip

.PHONY: release clean tag