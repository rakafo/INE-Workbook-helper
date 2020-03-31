alias r1="telnet_to r1"
alias r2="telnet_to r2"
alias r3="telnet_to r3"
alias r4="telnet_to r4"
alias r5="telnet_to r5"
alias r6="telnet_to r6"
alias r7="telnet_to r7"
alias r8="telnet_to r8"
alias r9="telnet_to r9"
alias r10="telnet_to r10"

telnet_to() {
    IP=148.251.122.103
    PORT=2100

    #set tab name
    echo -ne "\033]30;$1\007"

    port_arg=$(echo $1 | cut -c 2-)
    port_no=$[$PORT + $port_arg]
    echo "connecting to $1 ($IP $port_no)"
    telnet $IP $port_no
}
