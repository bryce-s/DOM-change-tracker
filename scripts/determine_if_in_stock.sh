#!/usr/bin/bash

# return 1 if not in stock, else return 0.
# currently waits for arg1 if not given...

output=$(grep -c ">We're sorry" $1)
if [ $? -ne 1 ]; then
	echo not in stock! 
	exit 1
fi

