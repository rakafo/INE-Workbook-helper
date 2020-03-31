#!/bin/bash
tmux kill-session -t routers
tmux new-session -d -s routers -n csr10
tmux send-keys -t "routers:csr10" r10 Enter
for i in range {1..10}; do
tmux new-window -t "routers:$i" -n csr$i
tmux send-keys -t "routers:csr$i" "r$i" Enter
done
tmux a -t routers
