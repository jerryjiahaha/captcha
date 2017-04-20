#! /usr/bin/env python3
# -*- coding: utf-8 -*-
# vim:fenc=utf-8
#
# Copyright © 2017 Jerry Jia <jerryjiahaha@gmail.com>
#
# Distributed under terms of the MIT license.

# NOTE >=python3.6 required

"""
Download captcha images
"""

from collections import UserDict
from random import randint, gauss
from pathlib import Path
import mimetypes
import copy
import re
import asyncio

# XXX maybe I can use https://github.com/hellysmile/fake-useragent ...
USER_AGENTS = [
        "Mozilla/5.0 (Windows NT 6.1) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/41.0.2228.0 Safari/537.36",
        "Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/41.0.2227.0 Safari/537.36",
        "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/42.0.2311.135 Safari/537.36 Edge/12.246",
        "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_9_3) AppleWebKit/537.75.14 (KHTML, like Gecko) Version/7.0.3 Safari/7046A194A",
        "Mozilla/5.0 (iPad; CPU OS 6_0 like Mac OS X) AppleWebKit/536.26 (KHTML, like Gecko) Version/6.0 Mobile/10A5355d Safari/8536.25",
        "Mozilla/5.0 (PLAYSTATION 3; 3.55)",
        "Mozilla/5.0 (Windows NT 6.1; WOW64) AppleWebKit/537.1 (KHTML, like Gecko) Chrome/21.0.1180.89 Safari/537.1 QIHU 360SE",
        "Mozilla/4.0 (compatible; MSIE 7.0; Windows NT 6.1; Trident/5.0; SLCC2; .NET CLR 2.0.50727; .NET CLR 3.5.30729; .NET CLR 3.0.30729; Media Center PC 6.0; 360SE)",
        "Mozilla/5.0 (PlayStation 4 1.000) AppleWebKit/536.26 (KHTML, like Gecko)",
        "Mozilla/5.0 (Playstation Vita 1.61) AppleWebKit/531.22.8 (KHTML, like Gecko) Silk/3.2",
        "Mozilla/5.0 (compatible; Konqueror/4.1; OpenBSD) KHTML/4.1.4 (like Gecko)",
        "Mozilla/5.0 (compatible; Konqueror/4.5; FreeBSD) KHTML/4.5.4 (like Gecko)",
        "Mozilla/5.0 (Macintosh; U; Intel Mac OS X 10.5; ko; rv:1.9.1b2) Gecko/20081201 Firefox/3.1b2",
        ]


class http_header(UserDict):
    required_headers = ('Host', )
    _pattern = re.compile(r"[^a-zA-Z0-9]")
    _pattern2 = re.compile(r"[^a-zA-Z]")
    @staticmethod
    def camel(key: str):
        """ convert abc-def to Abc-Def format """
        sep_str = key.split('-')
        dispatchers = [http_header.validate, http_header.upper_first,]
        def app(key):
            for f in dispatchers:
                # f1(f0(key))
                key = f(key)
            return key
        output = []
        for key in sep_str:
            output.append(app(key))
#        list(map(lambda k: list(map(lambda f: f(k), dispatchers)), sep_str))
        return '-'.join(output)

    @staticmethod
    def validate(key):
        if http_header._pattern.search(key) or http_header._pattern2.match(key):
            raise KeyError(f"Invalid key {key}")
        return key

    @staticmethod
    def upper_first(key: str):
        k0 = ord(key[0])
        if k0 not in range(ord('A'), ord('Z')):
            k0 = k0 - ord('a') + ord('A')
            key = key.replace(key[0], chr(k0), 1)
        return key

    def __setitem__(self, key: str, val: str):
        self.data[self.camel(key)] = val

    def __getitem__(self, key: str):
        return self.data[self.camel(copy.copy(key))]

    @staticmethod
    def parseFrom(content: str, header = None):
        header = http_header() if header is None else header
        datas = content.split("\r\n")
        for data in datas:
            try:
                key, _, val = data.partition(": ")
                header[key] = val.strip(' ')
            except:
                pass
        return header

    def dump(self, req = True):
        output = []
        if req:
            for h in self.required_headers:
                try:
                    v = self.data[h]
                    output.append(f"{h}: {v}")
                except:
                    pass
        for k, v in self.data.items():
            if k not in self.required_headers:
                output.append(f"{k}: {v}")
        return "\r\n".join(output)

def print_v(*args, verbose = True, **kwargs):
    if verbose:
        print(*args, **kwargs)

class http_client:
    protos = {
            'http': 80,
            'https': 443,
            }

    @staticmethod
    def extract_url(url: str):
        for p in http_client.protos.keys():
            urlhead = f"{p}://"
            found = url.find(urlhead)
            if found != -1:
                return (url[found + len(urlhead):], p,)
        return (url, 'http',)

    @staticmethod
    async def get(url: str, output = None, verbose = False):
        # step1 parse url
        url, proto = http_client.extract_url(url)
        print_v(url, proto, verbose = verbose)
        host = url.split('/')[0]
        if ':' in host:
            port = host.rpartition(':')[-1]
            host = host.rpartition(':')[0]
        else:
            port = http_client.protos[proto]
        path = '/' if host == url else url[len(host):]

        # step2 construct query
        ua = USER_AGENTS[randint(0, len(USER_AGENTS) - 1)]
        headers = http_header()
        headers['host'] = host
        headers['user-agent'] = ua
        headers['Accept'] = '*/*'
        headers['x-forwarded-for'] = "1.2.3.4"
        dump_header = headers.dump()
        to_send = f"GET {path} HTTP/1.1\r\n{dump_header}\r\n\r\n"
        print_v(to_send, verbose = verbose)
        print_v(host, port, verbose = verbose)
        ssl = True if proto == 'https' else False

        # step3 send request
        reader, writer = await asyncio.open_connection(host, port, ssl = ssl)
        writer.write(to_send.encode())

        # step4 read response
        header = http_header()

        # step4.1 get http response state
        res_state = await asyncio.wait_for(reader.readline(), 10) # timeout: 10s

        # step4.2 get http response header
        while True:
            got = await asyncio.wait_for(reader.readline(), 10)
            print_v("got:", got, verbose = verbose)
            if got == b'\r\n':
                break
            header = http_header.parseFrom(got.decode(), header)
        print_v(header.dump(), verbose = verbose)
        try:
            body_length = int(header['Content-Length'])
            content_type = header['Content-Type']
        except KeyError:
            return

        # step 4.3 get http body
        body = b''
        while len(body) < body_length:
            body += await asyncio.wait_for(reader.readexactly(1), 10)
        print_v(body, verbose = verbose)

        # step 5 process http response
        if output is None:
            return
        outpath = Path(output)
        if outpath.suffix == '':
            guess_ext = mimetypes.guess_extension(content_type)
            outpath = Path(f"{outpath}{guess_ext}")
        # TODO use async write
        outpath.write_bytes(body)

    @staticmethod
    async def loop_get(url: str, loop = 1, prefix: str = 'output', **kwargs):
        print(url)
        for i in range(loop):
            await http_client.get(url, f"{prefix}_{i}", **kwargs)
            print(f"{i}")
            await asyncio.sleep(abs(gauss(2, 1)))

if __name__ == '__main__':
    from argparse import ArgumentParser
    parser = ArgumentParser()
    parser.add_argument('url', help = "request url")
    parser.add_argument('-o', '--output', help = "output file prefix", default = "output")
    parser.add_argument('-l', '--loop', help = "loop counter", type = int, default = 1)
    parser.add_argument('-v', '--verbose', help = "verbose output", type = bool, default = False)
    args = parser.parse_args()

    loop = asyncio.get_event_loop()

    cli = http_client.loop_get(args.url, args.loop, args.output, verbose = args.verbose)

    loop.run_until_complete(cli)
