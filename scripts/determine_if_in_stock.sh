#!/usr/bin/bash
# $1 = url
# return 1 if not in stock, else return 0.
# currently waits for arg1 if not given...

output=$(phantomjs ./scripts/save_page.js $1 | grep -c ">We're sorry")
if [ $? -ne 1 ]; then
	echo not in stock! 
	exit 1
fi
echo in stock!
