#!/usr/bin/bash
if [[ "$OSTYPE" == "linux-gnu" ]]; then
	sudo apt-get install phantomjs
elif [[ "$OSTYPE" == "darwin"* ]]; then
	brew install phantomjs

