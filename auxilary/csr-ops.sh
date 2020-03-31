#!/bin/bash

#$1 must be resume or sleep
for i in {1..10}; do virsh $1 csr$i; done
