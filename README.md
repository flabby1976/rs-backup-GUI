# rs-backup-GUI
A GUI front-end for rs-backup-suite

https://stackoverflow.com/questions/4385656/tkinter-how-to-make-a-system-tray-application

### ON THE CLIENT

Install cygwin selecting extra packages wget, unzip, rsnapshot, nano

In cygwin shell, download and install rs-backup

    wget https://github.com/flabby1976/rs-backup-suite/archive/master.zip
    unzip master.zip
    cd rs-backup-suite-master/
    ./install.sh client

Again, in cygwin shell, create keys for server ssh access 

    ssh-keygen -t rsa -N '' -f ~/.ssh/id_rsa <<< y

copy public keys to server somehow - e.g. -

    scp ~/.ssh/id_rsa.pub root@fileserver:

### ON THE SERVER

Log on and add a user for the new client 

    rs-add-user [client-hostname] [client-username] id_rsa

