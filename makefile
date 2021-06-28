all: sensor sensor.service
.PHONY: all sensorservice install uninstall
lib_dir=/usr/local/lib/sensor
conf_dir=/usr/local/etc/sensor
service_dir=/etc/systemd/system
venv=$(lib_dir)/venv
configfile_dir=/boot/
oldconfigfile_dir=oldtxt/

install: $(service_dir) sensor.service
	@echo Installing the service files....
	cp sensor.service $(service_dir)
	chown root:root $(service_dir)/sensor.service
	chmod 644 $(service_dir)/sensor.service

	@echo Copying original config.txt
	cp $(configfile_dir)config.txt $(oldconfigfile_dir)
	@echo Overwriting old config.txt
	cp config.txt $(configfile_dir)

	@echo Installing library files...
	mkdir -p $(lib_dir)
	mkdir -p $(lib_dir)/bme680
	mkdir -p $(lib_dir)/tsys01
	cp readings.py $(lib_dir)
	cp bme680/* -R $(lib_dir)/bme680
	cp tsys01/* -R $(lib_dir)/tsys01
	chown pi:pi $(lib_dir)/*
	chmod 644 $(lib_dir)/*

	@echo Installing configuration files...
	mkdir -p $(conf_dir)
	cp .env $(conf_dir)
	chown root:root $(conf_dir)/
	chmod 644 $(conf_dir)/
	
	@echo Creating python virtual environment and installing packages...
	python3 -m venv $(venv)
	$(venv)/bin/pip3 install -r requirements.txt

	@echo Installing relevant linux packages...
	sudo apt-get install libopenjp2-7
	sudo apt-get install libtiff5
	
	@echo Installing log2ram
	git clone https://github.com/azlux/log2ram 
	@echo Setting up log2ram-config
	chmod +x /home/pi/bin/DepotKontroll/log2ram/install.sh
	cd /home/pi/bin/DepotKontroll/log2ram/ && sudo ./install.sh
	
	
	@echo installation complete...
	@echo run 'systemctl start sensor.service' to start service
	@echo run 'systemctl status sensor.service' to view status

uninstall:
	-systemctl stop sensor.service
	-systemctl disable sensor.service
	
	@echo removing modified config.txt, replacing with original.
	cp $(oldconfigfile_dir)config.txt $(configfile_dir)
	
	@echo removing relevant linux packages...
	sudo apt -y remove libopenjp2-7
	sudo apt -y remove libtiff5
	
	
	cd /home/pi/bin/DepotKontroll/log2ram && sudo ./uninstall.sh
	-rm -r $(lib_dir)
	-rm -r $(conf_dir)
	-rm -r $(service_dir)/sensor.service

