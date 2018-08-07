To enable this, change the (by default commented) lines in
/etc/sshd/sshd_config to:

    AuthorizedKeysCommand /usr/bin/ssh-key-retriever
    AuthorizedKeysCommandUser root

The config file is found in /etc/ssh-key-retriever.json.conf
