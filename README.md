# vpnonline-openvpn
a basic script for connecting to VPNonline servers via OpenVPN

## usage
on startup the script looks for configuration at `~/.vpnonline`,
credentials are stored in `~/.vpnonline/credentials.txt` with permissions `0600`,
definitions are located in `~/.vpnonline/definitions/` as `.ovnp` files

if credentials are missing, user will be asked to provide them, definitions are automatically fetched from VPNonline website 
```
$ sudo ./vpnonline.py [...]
user-name: ...
user-pass: ...
```

### --connect [index]
establish connection described by nth-definition

```
$ sudo ./vpnonline.py --connect 99
Wed Aug  5 01:04:29 2020 OpenVPN 2.4.7 x86_64-pc-linux-gnu [SSL (OpenSSL)] [LZO] [LZ4] [EPOLL] [PKCS11] [MH/PKTINFO] [AEAD] built on Sep  5 2019
Wed Aug  5 01:04:29 2020 library versions: OpenSSL 1.1.1f  31 Mar 2020, LZO 2.10
...
Wed Aug  5 01:05:31 2020 Initialization Sequence Complete
...
```

### --list
print enumerated list of all available definitions

```
$ sudo ./vpnonline.py --list
...
30  Latvia.ovpn
31  Lithuania.ovpn
32  Luxemburg.ovpn
...
```

### --search [keyword1] [keyword2] ...
print enumerated list of definitions containing all provided keywords,
matches will be highlighted, if `colorama` is available, or enclosed in square brackets otherwise

```
$ sudo ./vpnonline.py --search usa http
99  [USA].3-Dallas-[HTTP]S.ovpn 
100 [USA].3-New York-[HTTP]S.ovpn
```

### --detach
don't capture output, nor wait for connection subprocess to finish

```
$ sudo ./vpnonline.py --connect 99 --detach
$ ps -e | grep openvpn
  27020 pts/0    00:00:00 openvpn
```

### --reset-definitions
removes fetched definitions, (removes `~/.vpnonline/definitions`)

```
$ sudo ./vpnonline.py --reset-definitions
```

### --reset-credentials
removes saved credentials, (removes `~/.vpnonline/credentials.txt`)

```
$ sudo ./vpnonline.py --reset-credentials
```

### --reset
removes definitions and credentials, (removes `~/.vpnonline`)

```
$ sudo ./vpnonline.py --reset
```
