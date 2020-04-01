#!/bin/bash
tmux kill-session -t routers
tmux new-session -d -s routers -n csr10
tmux send-keys -t "routers:r10" r10 Enter
tmux send-keys -t "routers:r$i" "" Enter
tmux send-keys -t "routers:r$i" "enable" Enter
tmux send-keys -t "routers:r$i" "configure terminal" Enter
for i in range {1..9}; do
tmux new-window -t "routers:$i" -n r$i
tmux send-keys -t "routers:r$i" "r$i" Enter
tmux send-keys -t "routers:r$i" "" Enter
tmux send-keys -t "routers:r$i" "enable" Enter
tmux send-keys -t "routers:r$i" "configure terminal" Enter
done
tmux a -t routers
