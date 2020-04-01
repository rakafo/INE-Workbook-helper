#!/bin/bash

# kill if exists
tmux kill-session -t routers

# create new session, also window opened by default, so name it r10
tmux new-session -d -s routers -n r10
# create windows for r 1-9
for i in range {1..9}; do
  tmux new-window -t "router:$i" -n r$i
done

# commands to reach desired state in each window
for i in range {1..10}; do
tmux send-keys -t "routers:r$i" "r$i" Enter
tmux send-keys -t "routers:r$i" "" Enter
tmux send-keys -t "routers:r$i" "enable" Enter
tmux send-keys -t "routers:r$i" "configure terminal" Enter
done

# attach
tmux a -t routers
